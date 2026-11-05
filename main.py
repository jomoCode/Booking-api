from fastapi import FastAPI, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from database import engine, Base, get_db, SessionLocal
import models
import schemas
from datetime import datetime, timedelta
from auth import verify_api_key

# SlowApi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize Rate Limiter tracking by client IP address
limiter = Limiter(key_func=get_remote_address)

# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Clinic Booking API",
    description="API for patients to view slots, book appointments, and manage bookings.",
    version="1.0.0",
    dependencies=[Depends(verify_api_key)],
)

# Attach rate limiter state and exception handler to FastAPI app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Clinic Booking API! Head to /docs for the interactive documentation."
    }


# Helper function to seed sample slots on startup if none exist
@app.on_event("startup")
def seed_slots():
    db = SessionLocal()  # Directly create a session instance
    try:
        existing_slots = db.query(models.Slot).count()
        if existing_slots == 0:
            now = datetime.utcnow().replace(
                minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
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


@app.post(
    "/bookings",
    response_model=schemas.BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def create_booking(
    booking_in: schemas.BookingCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Book a slot safely with idempotency support via headers."""

    # If a key was provided, check if we already processed this request
    if idempotency_key:
        existing_booking = (
            db.query(models.Booking)
            .filter(models.Booking.idempotency_key == idempotency_key)
            .first()
        )
        if existing_booking:
            return existing_booking  # Return existing booking

    # ATOMIC CONCURRENCY CHECK: Claim the slot
    rows_updated = (
        db.query(models.Slot)
        .filter(models.Slot.id == booking_in.slot_id, models.Slot.is_booked == False)
        .update({"is_booked": True}, synchronize_session=False)
    )

    if rows_updated == 0:
        slot = (
            db.query(models.Slot).filter(models.Slot.id == booking_in.slot_id).first()
        )
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        raise HTTPException(status_code=400, detail="This slot is already booked")

    # 3. Create the booking record, storing the idempotency key if present
    db_booking = models.Booking(
        slot_id=booking_in.slot_id,
        patient_name=booking_in.patient_name,
        patient_email=booking_in.patient_email,
        idempotency_key=idempotency_key,
    )

    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

@app.post("/slots/reset", response_model=list[schemas.SlotResponse], status_code=status.HTTP_201_CREATED)
def reset_and_replace_slots(
    payload: schemas.SlotReplaceRequest,
    db: Session = Depends(get_db)
):
    """Deletes every booking and replaces all slots with the ones provided (including past slots)."""
    
    # 1. Delete all bookings first to avoid foreign key violations
    db.query(models.Booking).delete()
    
    # 2. Delete all existing slots
    db.query(models.Slot).delete()
    
    # 3. Insert the new slots supplied in the request payload
    created_slots = []
    for slot_data in payload.slots:
        db_slot = models.Slot(
            start_time=slot_data.start_time,
            end_time=slot_data.end_time,
            is_booked=False
        )
        db.add(db_slot)
        created_slots.append(db_slot)
        
    db.commit()
    
    # Refresh to populate database-generated IDs
    for slot in created_slots:
        db.refresh(slot)
        
    return created_slots



@app.get("/bookings", response_model=list[schemas.BookingResponse])
def list_bookings(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max number of records to return"),
    email: str | None = Query(
        default=None, description="Filter bookings by patient email"
    ),
    db: Session = Depends(get_db),
):
    """List bookings with pagination and optional email filter."""
    query = db.query(models.Booking)
    if email:
        query = query.filter(models.Booking.patient_email == email)

    bookings = query.offset(skip).limit(limit).all()
    return bookings


@app.get("/bookings/{booking_id}", response_model=schemas.BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Look up a booking by its ID."""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@app.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    """Cancel a booking, freeing up the slot for someone else."""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Find the slot and free it up
    slot = db.query(models.Slot).filter(models.Slot.id == booking.slot_id).first()
    if slot:
        slot.is_booked = False

    # Delete the booking record
    db.delete(booking)
    db.commit()
    return None
