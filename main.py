from fastapi import FastAPI
from database import engine, Base

# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Clinic Booking API",
    description="API for patients to view slots, book appointments, and manage bookings.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Clinic Booking API! Head to /docs for the interactive documentation."}