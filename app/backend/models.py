from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="patient") # doctor or patient

    records = relationship("HealthRecord", back_populates="user")

class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_path = Column(String) # Path to the uploaded MRI image
    prediction_result = Column(String) # 'No Tumor', 'Glioma', etc.
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True) # Doctor's notes

    user = relationship("User", back_populates="records")
