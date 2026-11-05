# Clinic Booking API

A REST API for viewing clinic appointment slots and creating, listing, and cancelling bookings. Built with FastAPI, SQLAlchemy, SQLite, Pydantic, and SlowAPI.

## Features

- View available appointment slots
- Create a booking for an available slot
- Prevent duplicate or concurrent bookings
- Support `Idempotency-Key` to retry booking requests safely
- List bookings with pagination and email filtering
- View or cancel an individual booking
- Replace all appointment slots
- API key authentication
- Booking rate limiting: 5 requests per minute
- Automatic creation and population of SQLite tables and sample slots

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic / Email Validator
- SlowAPI
- Uvicorn

## Project Structure

```text
clinic-booking-api/
├── auth.py
├── database.py
├── main.py
├── models.py
├── schemas.py
├── clinic.db
├── venv/
├── .gitignore
└── README.md
```

## Installation

### 1. Clone or open the project

```powershell
cd clinic-booking-api
```

### 2. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install fastapi uvicorn sqlalchemy pydantic email-validator slowapi
```

### 4. Start the API

```powershell
uvicorn main:app --reload
```

The API is available at:

- Base URL: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Authentication

Every endpoint requires an API key in the `x-api-key` header.

```text
x-api-key: my-secret-clinic-key-123
```

Swagger UI can authenticate by clicking **Authorize**, entering the key, and selecting **Authorize**.

> For production, move the API key from `auth.py` to an environment variable or secret manager.

## Database

The SQLite database is configured in `database.py`:

```text
clinic.db
```

The database and tables are created automatically when the application starts. If no slots exist, five hourly slots are added for the next day. The seeding process only runs when the `slots` table is empty.

## API Endpoints

### Welcome

```http
GET /
```

Returns a welcome message.

### List Available Slots

```http
GET /slots
```

Returns slots where `is_booked` is `false`.

Example:

```powershell
curl.exe -H "x-api-key: my-secret-clinic-key-123" http://127.0.0.1:8000/slots
```

### Create Booking

```http
POST /bookings
```

Request body:

```json
{
  "slot_id": 1,
  "patient_name": "John Doe",
  "patient_email": "john@example.com"
}
```

Optional header for safe retries:

```text
Idempotency-Key: booking-request-001
```

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/bookings `
  -H "x-api-key: my-secret-clinic-key-123" `
  -H "Idempotency-Key: booking-request-001" `
  -H "Content-Type: application/json" `
  -d '{"slot_id":1,"patient_name":"John Doe","patient_email":"john@example.com"}'
```

This endpoint is limited to five requests per minute per client IP.

### Replace All Slots

```http
POST /slots/reset
```

Request body:

```json
{
  "slots": [
    {
      "start_time": "2026-11-06T09:00:00",
      "end_time": "2026-11-06T09:45:00"
    },
    {
      "start_time": "2026-11-06T10:00:00",
      "end_time": "2026-11-06T10:45:00"
    }
  ]
}
```

> This endpoint deletes all existing bookings and then replaces all slots.

### List Bookings

```http
GET /bookings?skip=0&limit=10
```

Optional email filter:

```http
GET /bookings?email=john@example.com&skip=0&limit=10
```

- `skip`: number of records to skip; default is `0`
- `limit`: records per page; minimum `1`, maximum `100`, default is `10`
- `email`: filter by exact patient email

### Get a Booking

```http
GET /bookings/{booking_id}
```

Example:

```powershell
curl.exe -H "x-api-key: my-secret-clinic-key-123" http://127.0.0.1:8000/bookings/1
```

### Cancel a Booking

```http
DELETE /bookings/{booking_id}
```

Cancelling a booking removes it and marks its associated slot as available.

## Status Codes

| Status | Meaning                                |
| ------ | -------------------------------------- |
| `200`  | Request succeeded                      |
| `201`  | Booking or slots created               |
| `204`  | Booking cancelled successfully         |
| `403`  | Missing or invalid API key             |
| `404`  | Slot or booking not found              |
| `429`  | Rate limit exceeded                    |
| `400`  | Slot already booked or request invalid |
| `422`  | Request validation failed              |

## Development Notes

- SQLAlchemy sessions are supplied through FastAPI dependencies and closed after each request.
- Booking creation uses an atomic database update to mark a slot as booked before creating the booking.
- `Idempotency-Key` prevents repeated booking requests with the same key from creating duplicate bookings.
- SQLite is suitable for local development and small applications. Consider PostgreSQL for a production deployment requiring multiple server processes.

## License

Add a license here if you intend to distribute the project publicly.
