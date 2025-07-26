from sqlalchemy import Column, String, Boolean, Time, Date, Text, ForeignKey, UUID, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


#sqlalchemy orm model for the users table

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone_number = Column(String(20))
    timezone = Column(String(50), nullable=False)
    notification_preference = Column(String(10), nullable=False)

    daily_start_time = Column(Time, nullable=False)
    daily_end_time = Column(Time, nullable=False)

    trigger_type = Column(String(10), nullable=False) 
    trigger_time = Column(Time)
    trigger_habit = Column(Text)

    tone = Column(String(255), nullable=False)
    buddy_name = Column(String(255), nullable=False)
    mantra = Column(Text)

    is_hackathon_demo = Column(Boolean, default=False)

    monday_hour_1_enabled = Column(Boolean, default=False)
    monday_hour_1_day_of_week = Column(String(10))
    monday_hour_1_time = Column(Time)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    goals = relationship('Goal', back_populates="user", cascade="all, delete-orphan")

    daily_logs = relationship("DailyLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
    
#goals table

class Goal(Base):
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal_text = Column(Text, nullable=False)
    goal_duration_type = Column(String(20), nullable=False) 
    goal_duration_value = Column(Text) 

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="goals")

    def __repr__(self):
        return f"<Goal(id={self.id}, user_id={self.user_id}, goal_text='{self.goal_text[:20]}...')>"

#daily logs tbale

class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date = Column(Date, nullable=False)
    reflection_text = Column(Text)
    rating_score = Column(Integer) 

    log_type = Column(String(20), nullable=False, default='daily_reflection')

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="daily_logs")

    def __repr__(self):
        return f"<DailyLog(id={self.id}, user_id={self.user_id}, log_date={self.log_date})>"