import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Use SQLite by default for zero-config local dev; override with DATABASE_URL env var for PostgreSQL
_default_db = "sqlite:///./claimsense.db"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", _default_db)

# SQLite needs connect_args for thread safety with FastAPI
_connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database engine configured: %s", "SQLite" if "sqlite" in SQLALCHEMY_DATABASE_URL else "PostgreSQL")
except Exception as e:
    logger.error(f"Failed to configure database engine: {e}")
    engine = None
    SessionLocal = None

Base = declarative_base()

def get_db():
    """
    Dependency for FastAPI route handlers to get a database session.
    Yields the session and ensures it is closed after the request.
    """
    if SessionLocal is None:
        raise RuntimeError("Database engine is not configured. Check connection string.")
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
