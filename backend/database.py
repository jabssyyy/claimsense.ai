import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Default to local docker-compose setup if not provided
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/claimsense")

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database engine configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure database engine: {e}")
    # Create dummy engine and sessionmaker to prevent immediate crash if DB isn't running
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
