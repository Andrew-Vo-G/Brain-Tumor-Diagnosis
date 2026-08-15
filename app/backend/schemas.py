from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str
    full_name: str
    role: Optional[str] = "patient"
    height: Optional[float] = 0.0
    weight: Optional[float] = 0.0

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    username: Optional[str] = None

class PasswordChange(BaseModel):
    new_password: str

class HealthRecordResponse(BaseModel):
    id: int
    user_id: int
    image_path: str
    prediction_result: str
    confidence: float
    created_at: datetime
    notes: Optional[str] = None
    patient_name: Optional[str] = None
    zoom_path: Optional[str] = None
    gradcam_path: Optional[str] = None
    class Config:
        from_attributes = True

class SupabaseHealthRecord(BaseModel):
    # DTO match model for database row insertion via Supabase Dictionary format
    user_id: int
    image_path: str
    prediction_result: str
    confidence: float
    notes: Optional[str] = None

class HealthRecordUpdate(BaseModel):
    notes: Optional[str] = None

class MessageCreate(BaseModel):
    receiver_id: int
    content: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

class SymptomCreate(BaseModel):
    symptom_name: str
    severity: int
    notes: Optional[str] = None

class SymptomResponse(BaseModel):
    id: int
    user_id: int
    symptom_name: str
    severity: int
    logged_at: datetime
    notes: Optional[str] = None
    class Config:
        from_attributes = True

class AppointmentCreate(BaseModel):
    doctor_id: int
    appointment_date: datetime
    notes: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: datetime
    status: str
    notes: Optional[str] = None
    created_at: datetime
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None
    class Config:
        from_attributes = True
