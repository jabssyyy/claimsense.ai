"""
ClaimSense.ai - Submit Routes (M3 Clean Claim Guarantee)

API endpoints for final claim quality check and submission.

POST /submit-claim — Full M3 pipeline (code check, doc check, package assembly)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.claim_schema import ClaimSchema
from modules.m3_clean_claim import process_submission

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


# ---------------------------------------------------------------------------
# POST /submit-claim — Full M3 pipeline
# ---------------------------------------------------------------------------

@router.post("/submit-claim", response_model=SubmitClaimResponse)
async def submit_claim(request: SubmitClaimRequest):
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

    return SubmitClaimResponse(**result)
