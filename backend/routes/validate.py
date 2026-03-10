"""
ClaimSense.ai - Validate Routes (M2 Policy Rules Engine)

API endpoints for policy validation.

POST /validate-policy      — Validate a claim against a policy PDF (LLM-powered)
POST /validate-policy-demo — Validate using the built-in demo policy (no LLM needed)
"""

import base64
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from models.claim_schema import ClaimSchema
from modules.m2_policy_engine import validate_claim, validate_claim_with_mock_policy

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ValidatePolicyRequest(BaseModel):
    """Request body for full policy validation."""
    claim_json: dict                         # The claim to validate (from M1 output)
    policy_pdf_base64: Optional[str] = None  # Policy PDF as base64 string
    policy_text: Optional[str] = None        # OR: extracted policy text directly


class ValidateDemoRequest(BaseModel):
    """Request body for demo validation (no policy PDF needed)."""
    claim_json: dict                         # The claim to validate


class ValidateResponse(BaseModel):
    """Response from validation endpoints."""
    validation_results: list[dict]
    coverage_summary: Optional[str] = None
    policy_rules: dict
    validated_claim: dict
    overall_status: str                      # "PASS", "FAIL", or "WARNING"


# ---------------------------------------------------------------------------
# POST /validate-policy — Full validation with policy PDF
# ---------------------------------------------------------------------------

@router.post("/validate-policy", response_model=ValidateResponse)
async def validate_policy(request: ValidatePolicyRequest):
    """
    Validate a claim against an insurance policy.

    Provide the claim JSON (from M1) and either:
    - policy_pdf_base64: Base64-encoded policy PDF
    - policy_text: Extracted text from the policy

    Steps:
    1. Parse policy rules from the PDF using LLM (cached per policy)
    2. Run deterministic Python validation (PASS/FAIL/WARNING for each rule)
    3. Generate plain English coverage summary using LLM

    Returns validation results, coverage summary, and the updated claim.
    """
    logger.info("Policy validation request received")

    # Parse claim JSON into ClaimSchema
    try:
        claim = ClaimSchema(**request.claim_json)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claim JSON: {str(e)}",
        )

    # Determine policy input method
    policy_pdf_bytes = None
    policy_text = None

    if request.policy_pdf_base64:
        try:
            policy_pdf_bytes = base64.b64decode(request.policy_pdf_base64)
            logger.info("Policy PDF decoded: %d bytes", len(policy_pdf_bytes))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 policy PDF: {str(e)}",
            )
    elif request.policy_text:
        policy_text = request.policy_text
        logger.info("Policy text provided: %d chars", len(policy_text))
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'policy_pdf_base64' or 'policy_text'.",
        )

    # Run M2 pipeline
    try:
        result = validate_claim(
            claim=claim,
            policy_pdf_bytes=policy_pdf_bytes,
            policy_text=policy_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Validation failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Policy validation failed: {str(e)}",
        )

    return ValidateResponse(**result)


# ---------------------------------------------------------------------------
# POST /validate-policy-demo — Demo validation with built-in policy
# ---------------------------------------------------------------------------

@router.post("/validate-policy-demo", response_model=ValidateResponse)
async def validate_policy_demo(request: ValidateDemoRequest):
    """
    Validate a claim using the built-in demo policy.

    No policy PDF or Gemini API key needed. Uses a hardcoded Star Health-style
    policy with realistic limits for demonstration and testing.

    Rules in the demo policy:
    - Room rent limit: ₹5,000/day
    - Exclusions: dental, cosmetic surgery, maternity
    - Co-pay: 10%
    - ICU sub-limit: ₹10,000
    - OT sub-limit: ₹8,000
    - Pre-auth required: Yes
    - Sum insured: ₹5,00,000
    """
    logger.info("Demo validation request received")

    # Parse claim
    try:
        claim = ClaimSchema(**request.claim_json)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claim JSON: {str(e)}",
        )

    # Run with mock policy (no LLM)
    result = validate_claim_with_mock_policy(claim)

    return ValidateResponse(**result)
