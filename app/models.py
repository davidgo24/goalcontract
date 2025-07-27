from sqlalchemy import Column, String, Boolean, Time, Date, Text, ForeignKey, UUID, DateTime, Integer # Keep Integer for other models if needed
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime
import uuid 


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String) 
    phone_number = Column(String(20), unique=True, index=True)
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
    user_messages = relationship("UserMessage", back_populates="user", cascade="all, delete-orphan") # ADDED CASCADE

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

class Goal(Base): 
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id")) 
    description = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.now)
    target_date = Column(Date)
    is_completed = Column(Boolean, default=False)
    progress = Column(String, nullable=True)
    user = relationship("User", back_populates="goals") 


class DailyLog(Base): 
    __tablename__ = "daily_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id")) 
    date = Column(Date, index=True)
    message_type = Column(String)
    message_content = Column(String)
    ai_prompt_used = Column(String)
    sent_at = Column(DateTime, nullable=True)
    is_sent = Column(Boolean, default=False)
    user = relationship("User", back_populates="daily_logs")


class UserMessage(Base):
    __tablename__ = "user_messages" 

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id')) 
    message_content = Column(Text) 
                                   
    timestamp = Column(DateTime(timezone=True), default=func.now())
    sender_type = Column(String(10), default="user") 
    user = relationship("User", back_populates="user_messages")