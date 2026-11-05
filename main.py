from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import engine, Base, get_db, SessionLocal
import models
import schemas
from datetime import datetime, timedelta
from auth import verify_api_key


# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Clinic Booking API",
    description="API for patients to view slots, book appointments, and manage bookings.",
    version="1.0.0",
    dependencies=[Depends(verify_api_key)]
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Clinic Booking API! Head to /docs for the interactive documentation."}

# Helper function to seed sample slots on startup if none exist
@app.on_event("startup")
def seed_slots():
    db = SessionLocal()  # Directly create a session instance
    try:
        existing_slots = db.query(models.Slot).count()
        if existing_slots == 0:
            now = datetime.utcnow().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
            # Create 5 hourly slots for tomorrow
            for i in range(5):
                start = now + timedelta(hours=i)
                end = start + timedelta(minutes=45)
                db.add(models.Slot(start_time=start, end_time=end, is_booked=False))
            db.commit()
        else:
            print("slots already created")
    finally:
        db.close()

@app.get("/slots", response_model=list[schemas.SlotResponse])
def list_available_slots(db: Session = Depends(get_db)):
    """List all unbooked appointment slots."""
    slots = db.query(models.Slot).filter(models.Slot.is_booked == False).all()
    return slots


@app.post("/bookings", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(booking_in: schemas.BookingCreate, db: Session = Depends(get_db)):
    """Book an available slot with atomic concurrency protection."""
    
    # ATOMIC UPDATE CHECK: Try to claim the slot only if it is currently unbooked.
    rows_updated = db.query(models.Slot).filter(
        models.Slot.id == booking_in.slot_id,
        models.Slot.is_booked == False
    ).update({"is_booked": True}, synchronize_session=False)
    
    if rows_updated == 0:
        # Check slot even exists to give a precise 404 vs 400 error
        slot = db.query(models.Slot).filter(models.Slot.id == booking_in.slot_id).first()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        raise HTTPException(status_code=400, detail="This slot is already booked")
    
    # Create new booking record on success
    db_booking = models.Booking(
        slot_id=booking_in.slot_id,
        patient_name=booking_in.patient_name,
        patient_email=booking_in.patient_email
    )
    
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@app.get("/bookings/{booking_id}", response_model=schemas.BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Look up a booking by its ID."""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking