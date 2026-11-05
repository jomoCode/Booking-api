from datetime import datetime
from pydantic import BaseModel, EmailStr

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

class BookingResponse(BaseModel):
    id: int
    slot_id: int
    patient_name: str
    patient_email: EmailStr
    slot: SlotResponse

    class Config:
        from_attributes = True