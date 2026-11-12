import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Locally this falls back to SQLite. On Render, set DATABASE_URL to the
# Postgres connection string (Render's disk is wiped on every deploy/restart,
# so a SQLite file there would lose all bookings).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clinic.db")

# Render/Heroku hand out "postgres://" URLs; SQLAlchemy needs "postgresql://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_database_schema():
    """Add columns introduced after the initial database schema was created."""
    inspector = inspect(engine)
    if "bookings" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("bookings")}
    if "idempotency_key" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE bookings ADD COLUMN idempotency_key VARCHAR")
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_idempotency_key "
                    "ON bookings (idempotency_key)"
                )
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
