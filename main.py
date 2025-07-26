from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select 
from typing import Annotated 
import uuid
from schemas import UserCreate, UserResponse, GoalCreate, GoalResponse

from database import get_db

from models import User, Goal
from schemas import UserCreate, UserResponse, GoalCreate

app = FastAPI()

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
    
#user signup

@app.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(user_data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        existing_user = await db.execute(select(User).where(User.email == user_data.email))
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists."
            )

        user_dict = user_data.model_dump(exclude={"goal"})
        new_user = User(**user_dict)

        db.add(new_user)
        await db.flush() 

        new_goal = Goal(
            user_id=new_user.id, 
            **user_data.goal.model_dump()
        )

        db.add(new_goal)

        await db.commit() 
        await db.refresh(new_user) 
        await db.refresh(new_goal) 

        return UserResponse(
            id=new_user.id,
            name=new_user.name,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user or goal in database: {e}"
        )