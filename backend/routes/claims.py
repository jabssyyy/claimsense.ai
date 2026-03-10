"""
ClaimSense.ai - Claims Routes

API endpoints for retrieving saved claims from the database.

GET /claims       — List all claims (newest first)
GET /claims/{id}  — Get a single claim's full details
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import ClaimRecord

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ClaimListItem(BaseModel):
    """Single row in the claims list."""
    id: int
    claim_id: str
    status: str
    patient_name: Optional[str] = None
    hospital_name: Optional[str] = None
    total_bill: Optional[float] = None
    created_at: Optional[str] = None

class ClaimListResponse(BaseModel):
    """Response from GET /claims."""
    claims: list[ClaimListItem]
    total: int

class ClaimDetailResponse(BaseModel):
    """Response from GET /claims/{id}."""
    id: int
    claim_id: str
    status: str
    patient_name: Optional[str] = None
    hospital_name: Optional[str] = None
    total_bill: Optional[float] = None
    created_at: Optional[str] = None
    raw_data: Optional[dict] = None


# ---------------------------------------------------------------------------
# GET /claims — List all claims
# ---------------------------------------------------------------------------

@router.get("/claims", response_model=ClaimListResponse)
async def list_claims(db: Session = Depends(get_db)):
    """
    List all submitted claims, newest first.
    Returns summary fields for the table view.
    """
    records = db.query(ClaimRecord).order_by(ClaimRecord.created_at.desc()).all()

    claims = []
    for r in records:
        claims.append(ClaimListItem(
            id=r.id,
            claim_id=r.claim_id,
            status=r.status,
            patient_name=r.patient_name,
            hospital_name=r.hospital_name,
            total_bill=r.total_bill,
            created_at=r.created_at.isoformat() if r.created_at else None,
        ))

    return ClaimListResponse(claims=claims, total=len(claims))


# ---------------------------------------------------------------------------
# GET /claims/{id} — Single claim detail
# ---------------------------------------------------------------------------

@router.get("/claims/{claim_db_id}", response_model=ClaimDetailResponse)
async def get_claim(claim_db_id: int, db: Session = Depends(get_db)):
    """
    Get full details for a single claim, including the raw JSON data.
    """
    record = db.query(ClaimRecord).filter(ClaimRecord.id == claim_db_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")

    return ClaimDetailResponse(
        id=record.id,
        claim_id=record.claim_id,
        status=record.status,
        patient_name=record.patient_name,
        hospital_name=record.hospital_name,
        total_bill=record.total_bill,
        created_at=record.created_at.isoformat() if record.created_at else None,
        raw_data=record.raw_data,
    )
