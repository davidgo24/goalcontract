from typing import Annotated
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import datetime, logging, asyncio

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response


from .database import get_db
from .models import User, Goal, DailyLog
from .schemas import UserCreate, UserResponse, GoalResponse 
from .utils.ai_utils import generate_openai_message
from .utils import messaging_utils, email_utils



app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://goalcontract.vercel.app"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_time_label(time_obj: datetime.time) -> str:
    
    if isinstance(time_obj, datetime.datetime):
        time_obj = time_obj.time()
    return time_obj.strftime('%I:%M %p').lstrip("0")

def get_scheduled_times(start_time: datetime.time, end_time: datetime.time, trigger_time: datetime.time) -> dict:
    today = datetime.date.today()
    base = datetime.datetime.combine(today, start_time)
    end = datetime.datetime.combine(today, end_time)
    trigger = datetime.datetime.combine(today, trigger_time)
    wind_down_time = end - datetime.timedelta(hours=1.5) 

    
    
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    
    if end_minutes < start_minutes:
        end_minutes += 24 * 60 

    midpoint_minutes = start_minutes + (end_minutes - start_minutes) / 2
    midday_hour = int(midpoint_minutes // 60) % 24 
    midday_minute = int(midpoint_minutes % 60)

    midday_push_time_obj = datetime.time(midday_hour, midday_minute)

    return {
        "morning": base,
        "trigger": trigger,
        "midday": datetime.datetime.combine(today, midday_push_time_obj),
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
        print(f'Db test query: {current_time}')
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

@app.post("/simulate-day/{user_id}", summary="Simulate a full day of personalized system prompts", response_model=dict)
async def simulate_daily_support(user_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Simulates a day's system prompts based on user configuration and
    returns a preview of these messages for the frontend.
    """
    logging.info(f"DEBUG: Entering simulate_daily_support for user_id: {user_id}")
    try:
        logging.info("DEBUG: [1] Fetching user and goals from DB.")
        user_query = await db.execute(select(User).options(selectinload(User.goals)).where(User.id == user_id))
        user = user_query.scalars().first()
        logging.info("DEBUG: [1] User and goals fetched from DB.")

        if not user:
            logging.warning(f"DEBUG: User {user_id} not found.")
            raise HTTPException(status_code=404, detail="User not found")
        if not user.goals:
            logging.warning(f"DEBUG: User {user_id} has no associated goal.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must have at least one goal to run simulation.")

        goal_text = user.goals[0].description

        
        current_utc_datetime = datetime.datetime.now(datetime.timezone.utc)
        naive_utc_datetime = current_utc_datetime.replace(tzinfo=None)
        

        
        days_remaining_text = ""
        if user.goals[0].target_date:
            days_left = (user.goals[0].target_date - naive_utc_datetime.date()).days 
            if days_left >= 0: 
                days_remaining_text = f"\n\n⏳ {days_left} days until {goal_text.lower().replace('.', '')}"

       
        effective_trigger_time_for_scheduling = user.trigger_time if user.trigger_time else user.daily_start_time

        
        scheduled_times_dt = get_scheduled_times(user.daily_start_time, user.daily_end_time, effective_trigger_time_for_scheduling)

        prompts_and_configs = {
            "daily_system_initiation": { 
                "prompt": (
                    f"Write a short motivational morning message for '{user.full_name}'. "
                    f"Use the tone of '{user.tone}'. Their current goal is: '{goal_text}'. "
                    f"Focus: Begin daily flow, set a positive tone. Keep it concise (30-40 words). "
                    f"Avoid repeating their name in the body of the message."
                ),
                "base_label": "=== RISE N SHINE 🌄 ===", "emoji": "📜🤝",
                "add_days_remaining": False, "send_time_key": "morning"
            },
            "core_output_trigger": { 
                "prompt": (
                    f"For '{user.full_name}', after this habit/time: '{user.trigger_habit or format_time_label(user.trigger_time)}', "
                    f"remind them why they started working toward: '{goal_text}'. "
                    f"Use the tone '{user.tone}' and make it action-oriented. "
                    f"Do not mention their name in the message body. Keep it 30-40 words."
                ),
                "base_label": "=== TRIGGER 🔔 ===", "emoji": "🔔",
                "add_days_remaining": True, "send_time_key": "trigger"
            },
            "midday_push": { 
                "prompt": (
                    f"Write a calming and energizing midday message for '{user.full_name}'. "
                    f"The user’s mantra is: '{user.mantra or 'no mantra set'}'. "
                    f"Use the tone '{user.tone}'. Focus on presence, purpose, and choosing to make today count. "
                    f"Remind them life is a gift and they can still shape it. "
                    f"Keep it between 30 to 40 words and avoid repeating their name."
                ),
                "base_label": "=== MIDDAY PUSH ⚡️ ===", "emoji": "⚡️",
                "add_days_remaining": False, "send_time_key": "midday"
            },
            "daily_system_shutdown": { 
                "prompt": (
                    f"Write a reflective evening message for '{user.full_name}' in the tone of '{user.tone}'. "
                    f"Prompt them to rate their day 1–10 and share one win related to their goal: '{goal_text}'. "
                    f"Encourage jotting notes for clearing their mind and preparing for rest. "
                    f"Do not include their name in the message. Keep it between 30-40 words."
                ),
                "base_label": "=== WINDDOWN 🌚 ===", "emoji": "🌙",
                "add_days_remaining": False, "send_time_key": "wind_down"
            },
            "weekly_system_optimization": { 
                "prompt": (
                    f"Generate a concise 'Monday Hour 1' prompt for '{user.full_name}'. "
                    f"Tone: '{user.tone}'. Goal: '{goal_text}'. "
                    f"Focus: Review last week's system outputs and blueprint. Identify areas for optimization. "
                    f"Encourage a focused planning session for the week ahead. Max 40 words."
                ),
                "base_label": "🗓️ Monday Hour 1", "emoji": "📝",
                "add_days_remaining": False, "send_time_key": "weekly_override"
            }
        }

        message_keys_order = [
            "daily_system_initiation",
            "core_output_trigger",
            "midday_push",
            "daily_system_shutdown"
        ]
        if user.monday_hour_1_enabled:
            message_keys_order.append("weekly_system_optimization")

        saved_daily_log_entries = [] 
        formatted_messages_for_frontend = [] 

        for msg_key in message_keys_order:
            config = prompts_and_configs[msg_key]

            logging.info(f"DEBUG: Generating '{msg_key}' message with OpenAI.")
            
            ai_text = generate_openai_message(config["prompt"])
            

            
            timestamp_dt = None
            if config["send_time_key"] == "weekly_override":
                
                weekly_time = user.monday_hour_1_time if user.monday_hour_1_time else datetime.time(18, 0)
                timestamp_dt = datetime.datetime.combine(current_utc_datetime.date(), weekly_time)
            else:
                timestamp_dt = scheduled_times_dt.get(config["send_time_key"])

            timestamp_label = format_time_label(timestamp_dt.time()) if timestamp_dt else "N/A"

           
            full_msg_content = (
                f"{config['base_label']}\n\n"
                f"{ai_text}"
                f"{days_remaining_text if config['add_days_remaining'] else ''}"
                f"\n\n🕒 Scheduled: {timestamp_label}\n\n"
                f"– {user.buddy_name or 'System Feedback Loop'} {config['emoji']}"
            )

            
            message_sent_successfully = False

            
            if user.notification_preference in ["sms", "both"] and user.phone_number:
                try:
                    message_sid = messaging_utils.send_sms(to_number=user.phone_number, body=full_msg_content)
                    if message_sid: 
                        message_sent_successfully = True
                except Exception as e:
                    logging.error(f"ERROR: SMS failed for {msg_key} (user: {user.id}): {e}", exc_info=True)

            
            if user.notification_preference in ["email", "both"] and user.email:
                try:
                    
                    email_utils.send_email(
                        to_email=user.email,
                        message_type=config["base_label"],
                        message_body=full_msg_content,
                        buddy_name=user.buddy_name
                    )
                    message_sent_successfully = True 
                except Exception as e:
                    logging.error(f"ERROR: Email failed for {msg_key} (user: {user.id}): {e}", exc_info=True)
            

            
            daily_log_entry = DailyLog(
                user_id=user.id,
                date=naive_utc_datetime.date(),
                message_type=msg_key,
                message_content=full_msg_content,
                ai_prompt_used=config["prompt"],
                sent_at=naive_utc_datetime, 
                is_sent=message_sent_successfully 
            )
            db.add(daily_log_entry)
            saved_daily_log_entries.append(daily_log_entry)

            
            formatted_messages_for_frontend.append({
                "time": f"Simulated {config['base_label']} ({timestamp_label})",
                "content": full_msg_content,
                "note": ""
            })

            
            if user.is_hackathon_demo and msg_key != message_keys_order[-1]:
                print(f"\n✅ Generated and attempting to send '{msg_key}' message... simulating delay...\n")
                await asyncio.sleep(1) 

        logging.info("DEBUG: [6] Committing new daily log entries to DB.")
        await db.commit() 
        logging.info("DEBUG: [6] Daily log entries committed.")

        
        for entry in saved_daily_log_entries:
            await db.refresh(entry)
        logging.info("DEBUG: [7] Daily log entries refreshed.")

        return {
            "status": "success",
            "message": f"Simulated system prompts for {user.full_name}",
            "simulated_messages": formatted_messages_for_frontend 
        }

    except HTTPException:
        logging.error("ERROR: HTTPException raised in simulate_daily_support.", exc_info=True)
        raise
    except Exception as e:
        logging.error(f"ERROR: Unhandled exception in simulate_daily_support: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {e}"
        )

@app.post("/send-test-email/{user_id}")
async def send_test_email_to_user(user_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user or not user.email:
            raise HTTPException(status_code=404, detail="User not found or email not set")

        
        base_label = "=== TEST EMAIL 📧 ==="
        msg_body = (
            f"{base_label}\n\n"
            "This is a test email sent from GoalC to verify email delivery setup."
            f"\n\n🕒 Sent at: {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
            f"\n\n– {user.buddy_name or 'Bizzy'}"
        )

        email_utils.send_email( 
            to_email=user.email,
            message_type=base_label,
            message_body=msg_body,
            buddy_name=user.buddy_name
        )

        return {"status": "sent", "to": user.email}

    except Exception as e:
        logging.error(f"Email test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {e}")
    

