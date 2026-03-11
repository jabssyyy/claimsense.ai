"""
ClaimSense - Submit Routes (M3 Clean Claim Guarantee)

API endpoints for final claim quality check and submission.

POST /submit-claim — Full M3 pipeline (code check, doc check, package assembly)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.claim_schema import ClaimSchema
from modules.m3_clean_claim import process_submission
from database import get_db
from models.db_models import ClaimRecord

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SubmitClaimRequest(BaseModel):
    """Request body for claim submission."""
    validated_claim_json: dict                      # Validated claim from M2
    validation_results: Optional[list[dict]] = None # M2 validation results
    coverage_summary: Optional[str] = None          # M2 coverage summary
    skip_fhir: bool = True                          # Skip FHIR by default (needs LLM)


class SubmitClaimResponse(BaseModel):
    """Response from submission endpoint."""
    claim: dict
    validation_results: list[dict]          # M2 results carried forward
    coverage_summary: Optional[str]
    code_check_results: list[dict]          # M3 Step 1
    document_check_results: list[dict]      # M3 Step 2
    missing_items: list[dict]
    status: str                             # "Ready for Submission" or "Hold - Action Required"
    claim_reference: Optional[str]          # Generated on success
    fhir_payload: Optional[dict]
    db_id: Optional[int] = None             # ID from the PostgreSQL database


# ---------------------------------------------------------------------------
# POST /submit-claim — Full M3 pipeline
# ---------------------------------------------------------------------------

@router.post("/submit-claim", response_model=SubmitClaimResponse)
async def submit_claim(request: SubmitClaimRequest, db: Session = Depends(get_db)):
    """
    Final quality check and submission package assembly (M3).

    Steps:
    1. Medical code & integrity check (ICD-10 validation, department cross-check)
    2. Document completeness scan (required docs vary by claim type)
    3. Final submission package assembly (FHIR payload if all checks pass)

    If any critical issues are found: status = "Hold - Action Required"
    If everything passes: status = "Ready for Submission" + claim reference number

    Set skip_fhir=false to generate a FHIR-compliant payload (requires Gemini API key).
    """
    logger.info("Submission request received")

    # Parse claim
    try:
        claim = ClaimSchema(**request.validated_claim_json)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claim JSON: {str(e)}",
        )

    # Run M3 pipeline
    try:
        result = process_submission(
            claim=claim,
            validation_results=request.validation_results,
            coverage_summary=request.coverage_summary,
            skip_fhir=request.skip_fhir,
        )
    except Exception as e:
        logger.error("Submission processing failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Submission processing failed: {str(e)}",
        )

    # Persist the processed claim to PostgreSQL
    try:
        db_record = ClaimRecord(
            claim_id=claim.claim_id,
            status=result.get("status", "Unknown"),
            patient_name=claim.patient.name if getattr(claim, 'patient', None) else None,
            hospital_name=claim.hospital.name if getattr(claim, 'hospital', None) else None,
            total_bill=claim.billing.total_bill if getattr(claim, 'billing', None) else None,
            raw_data=result
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        result["db_id"] = db_record.id
        logger.info(f"Persisted claim {claim.claim_id} to DB with ID: {db_record.id}")
    except Exception as e:
        logger.error(f"Failed to persist claim to DB: {str(e)}")
        # We don't fail the API request if the database save fails for MVP,
        # but in production you'd want a rollback or retry queue.
        db.rollback()

    return SubmitClaimResponse(**result)


# ---------------------------------------------------------------------------
# PATCH /claims/{id}/submit-to-insurer — Mark claim as Submitted
# ---------------------------------------------------------------------------

@router.patch("/claims/{claim_db_id}/submit-to-insurer")
async def submit_to_insurer(claim_db_id: int, db: Session = Depends(get_db)):
    """
    Mark a claim as submitted to the insurer.
    Updates the status to 'Submitted' in the database.
    """
    record = db.query(ClaimRecord).filter(ClaimRecord.id == claim_db_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")

    record.status = "Submitted"
    db.commit()
    db.refresh(record)

    logger.info(f"Claim {record.claim_id} marked as Submitted (DB ID: {record.id})")

    return {
        "success": True,
        "message": f"Claim {record.claim_id} has been successfully submitted to the insurer.",
        "claim_id": record.claim_id,
        "status": "Submitted",
    }
