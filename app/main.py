from typing import Annotated
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import datetime, logging, asyncio

from .database import get_db
from .models import User, Goal, DailyLog
from .schemas import UserCreate, UserResponse, GoalResponse
from .utils.ai_utils import generate_openai_message
from .utils.email_utils import send_email
from .utils import messaging_utils, email_utils



app = FastAPI()


def format_time_label(time: datetime.datetime) -> str:
    return time.strftime('%I:%M %p').lstrip("0")

def get_scheduled_times(start_time: datetime.time, end_time: datetime.time, trigger_time: datetime.time) -> dict:
    base = datetime.datetime.combine(datetime.date.today(), start_time)
    end = datetime.datetime.combine(datetime.date.today(), end_time)
    trigger = datetime.datetime.combine(datetime.date.today(), trigger_time)
    wind_down_time = end - datetime.timedelta(hours=1.5)
    midday_push_time = base + (wind_down_time - base) / 2
    return {
        "morning": base,
        "trigger": trigger,
        "midday": midday_push_time,
        "wind_down": wind_down_time
    }

@app.get("/")
async def read_root():
    return {"message": "Sistema API Testing :)"}

@app.get("/test-db")
async def test_db_connection(db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        result = await db.execute(text("SELECT NOW() as current_db_time;"))
        current_time = result.scalar_one()
        return {"message": "DB connection successful!", "db_time": str(current_time)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Db connection failed {str(e)}')

@app.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(user_data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        existing_user = await db.execute(select(User).where(User.email == user_data.email))
        if existing_user.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists.")

        user_dict = user_data.model_dump(exclude={"goal"})
        new_user = User(**user_dict)
        db.add(new_user)
        await db.flush()

        new_goal = Goal(
            user_id=new_user.id,
            description=user_data.goal.goal_text,
            target_date=datetime.datetime.strptime(user_data.goal.goal_duration_value, "%Y-%m-%d").date()
            if user_data.goal.goal_duration_type == 'fixed' and user_data.goal.goal_duration_value else None
        )
        db.add(new_goal)

        await db.commit()
        await db.refresh(new_user)
        await db.refresh(new_goal)

        return UserResponse(
            id=new_user.id,
            full_name=new_user.full_name,
            email=new_user.email,
            phone_number=new_user.phone_number,
            timezone=new_user.timezone,
            notification_preference=new_user.notification_preference,
            daily_start_time=new_user.daily_start_time,
            daily_end_time=new_user.daily_end_time,
            trigger_type=new_user.trigger_type,
            trigger_time=new_user.trigger_time,
            trigger_habit=new_user.trigger_habit,
            tone=new_user.tone,
            buddy_name=new_user.buddy_name,
            mantra=new_user.mantra,
            is_hackathon_demo=new_user.is_hackathon_demo,
            monday_hour_1_enabled=new_user.monday_hour_1_enabled,
            monday_hour_1_day_of_week=new_user.monday_hour_1_day_of_week,
            monday_hour_1_time=new_user.monday_hour_1_time,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
            goal=GoalResponse.model_validate(new_goal)
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create user or goal in database: {e}")

@app.get("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user(user_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).options(selectinload(User.goals)).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.goals:
        raise HTTPException(status_code=500, detail="User found but no associated goal found.")
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        timezone=user.timezone,
        notification_preference=user.notification_preference,
        daily_start_time=user.daily_start_time,
        daily_end_time=user.daily_end_time,
        trigger_type=user.trigger_type,
        trigger_time=user.trigger_time,
        trigger_habit=user.trigger_habit,
        tone=user.tone,
        buddy_name=user.buddy_name,
        mantra=user.mantra,
        is_hackathon_demo=user.is_hackathon_demo,
        monday_hour_1_enabled=user.monday_hour_1_enabled,
        monday_hour_1_day_of_week=user.monday_hour_1_day_of_week,
        monday_hour_1_time=user.monday_hour_1_time,
        created_at=user.created_at,
        updated_at=user.updated_at,
        goal=GoalResponse.model_validate(user.goals[0])
    )

@app.post("/simulate-day/{user_id}", summary="Simulate a full day of personalized support", response_model=dict)
async def simulate_daily_support(user_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        result = await db.execute(select(User).options(selectinload(User.goals)).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.goals:
            raise HTTPException(status_code=400, detail="User must have at least one goal to run simulation.")

        goal_text = user.goals[0].description
        now = datetime.datetime.utcnow()
        messages = []
        send_sms_enabled = bool(user.phone_number)

        days_remaining_text = ""
        if user.goals[0].target_date:
            days_left = (user.goals[0].target_date - now.date()).days
            if days_left > 0:
                days_remaining_text = f"\n\n⏳ {days_left} days until {goal_text}"

        # Scheduled times
        scheduled_times = get_scheduled_times(user.daily_start_time, user.daily_end_time, user.trigger_time)

        prompts = {
            "morning": (
                f"Address the user by name: {user.full_name}. "
                f"Write a short motivational message in the tone of '{user.tone}'. "
                f"Their current goal is: '{goal_text}'. Avoid repeating their name in the body. "
                f"Keep the message concise (30–40 words)."
            ),
            "trigger": (
                f"After this habit: '{user.trigger_habit}', their day begins. "
                f"Remind them why they started working toward: '{goal_text}'. "
                f"Use the tone '{user.tone}' and make it action-oriented. "
                f"Do not mention their name in the message body. Keep it 30–40 words."
            ),
            "midday": (
                f"Write a calming and energizing midday message. "
                f"The user’s mantra is: '{user.mantra or 'no mantra set'}'. "
                f"Use the tone '{user.tone}'. "
                f"Focus on presence, purpose, and choosing to make today count. "
                f"Remind them life is a gift and they can still shape it. "
                f"Keep it between 30 to 40 words and avoid repeating their name."
            ),
            "wind_down": (
                f"Write a reflective evening message in the tone of '{user.tone}'. "
                f"Ask the user to rate their day 1–10 and share one win. "
                f"Their goal is: '{goal_text}'. Do not include their name in the message. "
                f"Keep it between 30–40 words."
            )
        }
        saved_logs = []
        for i, (msg_type, prompt) in enumerate(prompts.items()):
            ai_text = generate_openai_message(prompt).strip()
            timestamp = format_time_label(scheduled_times[msg_type])

            base_label = {
                "morning": "=== RISE N SHINE 🌄 ===",
                "trigger": "=== TRIGGER 🔔 ===",
                "midday": "=== MIDDAY PUSH ⚡️ ===",
                "wind_down": "=== WINDDOWN 🌚 ==="
            }[msg_type]

            emoji = {
                "morning": "📜🤝",
                "trigger": "🔔",
                "midday": "⚡️",
                "wind_down": "🌙"
            }[msg_type]

            msg_body = (
                f"{base_label}\n\n{ai_text}"
                f"{days_remaining_text if msg_type == 'trigger' else ''}"
                f"\n\n🕒 Scheduled: {timestamp}\n\n– {user.buddy_name} {emoji}"
            )

            sid = None
            sent = False
            channels_used = []

            # SMS (if enabled)
            if user.notification_preference in ["sms", "both"] and user.phone_number:
                try:
                    sid = messaging_utils.send_sms(user.phone_number, msg_body)
                    sent = True
                    channels_used.append("sms")
                except Exception as e:
                    logging.error(f"SMS failed for {msg_type}: {e}")

            # Email (if enabled)
            if user.notification_preference in ["email", "both"] and user.email:
                try:
                    email_utils.send_email(
                        to_email=user.email,
                        message_type=base_label,
                        message_body=msg_body,
                        buddy_name=user.buddy_name
                    )
                    sent = True
                    channels_used.append("email")
                except Exception as e:
                    logging.error(f"Email failed for {msg_type}: {e}")


            log = DailyLog(
                user_id=user.id,
                date=now.date(),
                message_type=msg_type,
                message_content=msg_body,
                ai_prompt_used=prompt,
                sent_at=now,
                is_sent=sent
            )
            db.add(log)
            saved_logs.append(log)

            if user.is_hackathon_demo and i < len(prompts) - 1:
                print(f"\n✅ Sent '{msg_type}' message... waiting 15 seconds before next...\n")
                await asyncio.sleep(15)

        await db.commit()
        for entry in saved_logs:
            await db.refresh(entry)

        return {
            "status": "success",
            "message": f"Simulated messages for {user.full_name}",
            "logged_messages_count": len(saved_logs),
            "logged_messages_ids": [str(x.id) for x in saved_logs]
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Unhandled error in simulate_daily_support: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")


app.post("/send-test-email/{user_id}")
async def send_test_email_to_user(user_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        # Fetch user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user or not user.email:
            raise HTTPException(status_code=404, detail="User not found or email not set")

        # Format a basic test message
        base_label = "=== TEST EMAIL 📧 ==="
        msg_body = (
            f"{base_label}\n\n"
            "This is a test email sent from GoalC to verify email delivery setup."
            f"\n\n🕒 Sent at: {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
            f"\n\n– {user.buddy_name or 'Bizzy'}"
        )

        send_email(
            to_email=user.email,
            message_type=base_label,
            message_body=msg_body,  
            buddy_name=user.buddy_name
        )

        return {"status": "sent", "to": user.email}

    except Exception as e:
        logging.error(f"Email test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {e}")
