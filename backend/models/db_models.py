import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from database import Base

class ClaimRecord(Base):
    """
    SQLAlchemy model representing a processed medical insurance claim.
    Stores high-level indexed fields for searching/dashboarding,
    and the full structured JSON output for complete records.
    """
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    
    # Generated ID (e.g., CLM-2026-ABCD)
    claim_id = Column(String, unique=True, index=True, nullable=False)
    
    # Processing Status (e.g., Extracted, Passed, Warning, Hold - Action Required, Rejected)
    status = Column(String, index=True, nullable=False)
    
    # High-level extracted fields for easy querying
    patient_name = Column(String, index=True, nullable=True)
    hospital_name = Column(String, index=True, nullable=True)
    total_bill = Column(Float, nullable=True)
    
    # Full ClaimSchema stored as JSONB
    # (Using basic JSON for broader compatibility, but Postgres JSONB is preferred in production)
    raw_data = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<ClaimRecord(claim_id='{self.claim_id}', status='{self.status}')>"
