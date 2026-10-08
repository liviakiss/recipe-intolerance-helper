from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Put it in backend/.env (local) or in the "
        "hosting service's environment variables (deployed)."
    )

# Some hosts hand out "postgres://", which SQLAlchemy no longer accepts.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

# pool_pre_ping tests a connection before using it. Free hosted databases
# close idle connections, and without this the first request after a quiet
# spell would fail with a dropped-connection error.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()