# app/schemas.py (Ensure this content is in your file!)
from pydantic import BaseModel, EmailStr, Field
from datetime import time, date, datetime
from typing import Optional, Literal
import uuid # Keep this for UUID fields in other schemas

# Pydantic Model for Goal creation
class GoalCreate(BaseModel):
    goal_text: str = Field(..., min_length=1, max_length=1000)
    goal_duration_type: Literal['fixed', 'estimate', 'ongoing']
    goal_duration_value: Optional[str] = None

    class Config:
        from_attributes = True 

# Pydantic Model for User creation
class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255) 
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=20)
    timezone: str = Field(..., max_length=50)
    notification_preference: Literal['sms', 'email', 'both']

    daily_start_time: time
    daily_end_time: time

    trigger_type: Literal['time', 'habit', 'both']
    trigger_time: Optional[time] = None
    trigger_habit: Optional[str] = Field(None, max_length=1000)

    tone: str = Field(..., max_length=255)
    buddy_name: str = Field(..., min_length=1, max_length=255)
    mantra: Optional[str] = Field(None, max_length=1000)

    is_hackathon_demo: bool = False

    monday_hour_1_enabled: bool = False
    monday_hour_1_day_of_week: Optional[Literal['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']] = None
    monday_hour_1_time: Optional[time] = None

    goal: GoalCreate

    class Config:
        from_attributes = True

# Pydantic Model for Goal response
class GoalResponse(BaseModel): 
    id: int 
    user_id: uuid.UUID
    description: str 
    created_at: datetime
    target_date: Optional[date] 
    is_completed: bool 
    progress: Optional[str] 

    class Config:
        from_attributes = True

# Pydantic Model for user response
class UserResponse(UserCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    goal: GoalResponse 

    class Config:
        from_attributes = True

# Pydantic Model for DailyLog (for future use, e.g., viewing logs)
class DailyLogResponse(BaseModel): 
    id: int 
    user_id: uuid.UUID
    date: date 
    message_type: str
    message_content: str
    ai_prompt_used: Optional[str] = None 
    sent_at: Optional[datetime] = None 
    is_sent: Optional[bool] = None 
    reflection_text: Optional[str] = None
    rating_score: Optional[int] = Field(None, ge=1, le=10)
    # log_type: Literal['daily_reflection', 'monday_hour_1'] 
                                                            
                                                            

    class Config:
        from_attributes = True