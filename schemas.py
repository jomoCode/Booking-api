from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator

class SlotResponse(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    is_booked: bool

    class Config:
        from_attributes = True

class BookingCreate(BaseModel):
    slot_id: int
    patient_name: str
    patient_email: EmailStr

    @field_validator('patient_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Patient name cannot be empty")
        if len(v.strip()) < 3:
            raise ValueError("Patient name must be at least 3 characters long")
        return v.strip()

class BookingResponse(BaseModel):
    id: int
    slot_id: int
    patient_name: str
    patient_email: EmailStr
    slot: SlotResponse

    class Config:
        from_attributes = True