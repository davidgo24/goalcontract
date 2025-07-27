from typing import Annotated
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import datetime, logging

from .database import get_db
from .models import User, Goal, DailyLog
from .schemas import UserCreate, UserResponse, GoalResponse
from .utils.ai_utils import generate_openai_message
from .utils import messaging_utils

app = FastAPI()

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

        # Countdown logic
        days_remaining_text = ""
        if user.goals[0].target_date:
            days_left = (user.goals[0].target_date - now.date()).days
            if days_left > 0:
                days_remaining_text = f"\n\n⏳ {days_left} days until {goal_text}"

        # Morning Message
        prompt_morning = (
            f"Write a short motivational message in the tone of '{user.tone}'. "
            f"Avoid greetings or repeating their name. Their buddy is '{user.buddy_name}'. "
            f"Their current goal is: '{goal_text}'. Keep it between 30 to 40 words."
        )
        text_morning = generate_openai_message(prompt_morning).strip()
        messages.append({
            "type": "morning",
            "prompt": prompt_morning,
            "content": f"=== RISE N SHINE 🌄 ===\n\n{text_morning}\n\n– {user.buddy_name} 📜🤝"
        })

        # Trigger Message
        prompt_trigger = (
            f"After this: '{user.trigger_habit}', their day begins. Remind them why they started their goal: '{goal_text}'. "
            f"Use the tone '{user.tone}'. Make it action-oriented, and sign off as '{user.buddy_name}'. "
            f"Keep it between 30 to 40 words."
        )
        text_trigger = generate_openai_message(prompt_trigger).strip()
        messages.append({
            "type": "trigger",
            "prompt": prompt_trigger,
            "content": f"=== TRIGGER 🔔 ===\n\n{text_trigger}{days_remaining_text}\n\n– {user.buddy_name} 🔔"
        })

        # Motivational Push
        prompt_motivational = (
            f"Write a concise motivational push for a user working toward '{goal_text}'. "
            f"Mantra: '{user.mantra or 'no mantra set'}'. Tone: '{user.tone}'. Sign as '{user.buddy_name}'. "
            f"Avoid repeating their name. Keep it between 30 to 40 words."
        )
        text_motivational = generate_openai_message(prompt_motivational).strip()
        messages.append({
            "type": "motivational",
            "prompt": prompt_motivational,
            "content": f"=== MIDDAY PUSH 👽 ===\n\n{text_motivational}\n\n– {user.buddy_name} 💪"
        })

        # Wind-Down Reflection
        prompt_wind_down = (
            f"Write a reflective evening message using a '{user.tone}' tone. "
            f"Ask user to rate day 1–10 and share a win. Goal: '{goal_text}'. Sign as '{user.buddy_name}'. "
            f"Avoid repeating their name. Keep it between 30 to 40 words."
        )
        text_wind_down = generate_openai_message(prompt_wind_down).strip()
        messages.append({
            "type": "wind_down",
            "prompt": prompt_wind_down,
            "content": f"=== WINDDOWN 🌚 ===\n\n{text_wind_down}\n\n– {user.buddy_name} 🌙"
        })

        # Save messages to DB
        saved_logs = []
        for m in messages:
            sid = None
            sent = False
            if send_sms_enabled:
                try:
                    sid = messaging_utils.send_sms(user.phone_number, m["content"])
                    sent = bool(sid)
                except Exception as e:
                    logging.error(f"SMS failed for {m['type']}: {e}")
            log = DailyLog(
                user_id=user.id,
                date=now.date(),
                message_type=m["type"],
                message_content=m["content"],
                ai_prompt_used=m["prompt"],
                sent_at=now,
                is_sent=sent
            )
            db.add(log)
            saved_logs.append(log)

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
