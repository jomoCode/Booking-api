from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./clinic.db"

# check_same_thread=False is needed for SQLite in FastAPI
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_database_schema():
    """Add columns introduced after the initial database schema was created."""
    with engine.begin() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "bookings" in tables:
            columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info(bookings)"
                ).fetchall()
            }
            if "idempotency_key" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE bookings ADD COLUMN idempotency_key VARCHAR"
                )
                connection.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_idempotency_key "
                    "ON bookings (idempotency_key)"
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
