"""
ClaimSense.ai - Module 2: Policy Rules Engine

Validates whether a claim qualifies for coverage under its insurance policy.

Three steps:
  Step 1 - Policy Parsing (LLM): Extract policy rules into structured JSON. Cached per policy.
  Step 2 - Deterministic Validation (Python): if-else logic for each rule. NEVER uses AI.
  Step 3 - Coverage Summary (LLM): Plain English summary of validation results.

CRITICAL DESIGN DECISION:
  AI is used ONLY for reading the policy (Step 1) and writing the summary (Step 3).
  All PASS/FAIL decisions are deterministic Python if-else logic (Step 2).
  This ensures consistent, auditable results every time.
"""

import logging
from typing import Dict, List, Optional

from models.claim_schema import (
    ClaimSchema,
    PolicyRules,
    PolicySubLimits,
    ValidationResult,
)
from services.llm_service import call_llm, call_llm_json
from services.pdf_service import extract_text_from_pdf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory policy cache (production would use database)
# Key: policy_id, Value: PolicyRules
# ---------------------------------------------------------------------------
_policy_cache: Dict[str, PolicyRules] = {}


# ---------------------------------------------------------------------------
# LLM Prompt Templates
# ---------------------------------------------------------------------------

POLICY_PARSING_SYSTEM = (
    "You are an insurance policy rules extractor for the Indian health insurance market."
)

POLICY_PARSING_PROMPT = """Read the following insurance policy document and extract all coverage rules into
a structured JSON object. Be precise. Use exact numbers from the policy.
Do not interpret or infer - only extract what is explicitly stated.

Return ONLY the JSON object. No explanation, no markdown, no extra text.

Extract these fields:
{{
  "policy_id": "",
  "insurer": "",
  "room_rent_limit_per_day": 0,
  "waiting_period_days": 0,
  "exclusions": [],
  "copay_percentage": 0,
  "sub_limits": {{"icu": 0, "ot": 0}},
  "cashless_eligible": true,
  "reimbursement_eligible": true,
  "pre_auth_required": true,
  "sum_insured": 0,
  "network_hospitals_only": false
}}

Policy document text:
{policy_text}"""

COVERAGE_SUMMARY_SYSTEM = (
    "You are a health insurance claims advisor writing for patients and hospital staff "
    "in India. Write in plain simple English. No insurance jargon."
)

COVERAGE_SUMMARY_PROMPT = """Based on the validation results below, write a clear summary explaining:
1. What is covered by the policy for this claim
2. What is not covered and exactly why
3. How much the patient owes vs how much the insurer will pay
4. What documents or information are still missing

Keep each point to one or two sentences. Use rupee amounts where relevant.
Write as if explaining to someone who has never read an insurance policy.

Validation results:
{validation_results}

Claim details:
{claim_summary}"""


# ---------------------------------------------------------------------------
# Step 1: Policy Parsing (LLM) — called once per policy, cached
# ---------------------------------------------------------------------------

def parse_policy_from_text(policy_text: str) -> PolicyRules:
    """
    Parse an insurance policy document into structured rules using LLM.

    The LLM reads the policy ONCE and extracts all rules as JSON.
    Result is cached by policy_id so subsequent claims under the same
    policy don't trigger another LLM call.

    Args:
        policy_text: Extracted text from the policy PDF.

    Returns:
        PolicyRules object with all extracted rules.
    """
    logger.info("Step 1: Parsing policy with LLM (%d chars)", len(policy_text))

    prompt = POLICY_PARSING_PROMPT.format(policy_text=policy_text)
    raw = call_llm_json(prompt=prompt, system=POLICY_PARSING_SYSTEM)

    # Parse sub_limits if present
    sub_limits_data = raw.get("sub_limits", {})
    if isinstance(sub_limits_data, dict):
        sub_limits = PolicySubLimits(
            icu=float(sub_limits_data.get("icu", 0)),
            ot=float(sub_limits_data.get("ot", 0)),
        )
    else:
        sub_limits = PolicySubLimits()

    rules = PolicyRules(
        policy_id=raw.get("policy_id"),
        insurer=raw.get("insurer"),
        room_rent_limit_per_day=float(raw.get("room_rent_limit_per_day", 0)),
        waiting_period_days=int(raw.get("waiting_period_days", 0)),
        exclusions=raw.get("exclusions", []),
        copay_percentage=float(raw.get("copay_percentage", 0)),
        sub_limits=sub_limits,
        cashless_eligible=bool(raw.get("cashless_eligible", True)),
        reimbursement_eligible=bool(raw.get("reimbursement_eligible", True)),
        pre_auth_required=bool(raw.get("pre_auth_required", True)),
        sum_insured=float(raw.get("sum_insured", 0)),
        network_hospitals_only=bool(raw.get("network_hospitals_only", False)),
    )

    # Cache by policy_id
    if rules.policy_id:
        _policy_cache[rules.policy_id] = rules
        logger.info("Policy cached: %s (%s)", rules.policy_id, rules.insurer)

    logger.info("Step 1 complete — %d exclusions, sum_insured=%.0f", len(rules.exclusions), rules.sum_insured)
    return rules


def parse_policy_from_pdf(pdf_bytes: bytes) -> PolicyRules:
    """
    Extract text from a policy PDF then parse the rules.

    Convenience wrapper: PDF → text extraction → LLM parsing.
    """
    text, page_count = extract_text_from_pdf(pdf_bytes)
    if not text.strip():
        raise ValueError(
            "Could not extract text from the policy PDF. "
            "Please ensure it is a digital PDF (not scanned)."
        )
    logger.info("Policy PDF: %d pages, %d chars extracted", page_count, len(text))
    return parse_policy_from_text(text)


def get_cached_policy(policy_id: str) -> Optional[PolicyRules]:
    """Return cached policy rules if available."""
    return _policy_cache.get(policy_id)


# ---------------------------------------------------------------------------
# Step 2: Deterministic Rules Validation (Pure Python — NO AI)
# ---------------------------------------------------------------------------

def validate_claim_against_policy(
    claim: ClaimSchema,
    rules: PolicyRules,
) -> List[ValidationResult]:
    """
    Validate a claim against policy rules using DETERMINISTIC Python logic.

    CRITICAL: No LLM calls here. Every decision is pure if-else logic.
    This ensures consistent, auditable results every single time.

    Each check returns PASS, FAIL, or WARNING with a specific reason.

    Args:
        claim: The claim to validate.
        rules: The parsed policy rules.

    Returns:
        List of ValidationResult objects, one per rule checked.
    """
    logger.info("Step 2: Deterministic validation starting")
    results: List[ValidationResult] = []

    # ---- 1. Room Rent Check ----
    if rules.room_rent_limit_per_day > 0:
        daily_room = claim.billing.room_charges
        los = claim.admission.length_of_stay or 1
        effective_daily = daily_room / los if los > 0 else daily_room

        if effective_daily <= rules.room_rent_limit_per_day:
            results.append(ValidationResult(
                rule="room_rent",
                status="PASS",
                reason=f"Room charges ₹{effective_daily:.0f}/day are within the policy limit of ₹{rules.room_rent_limit_per_day:.0f}/day.",
                amount=effective_daily,
            ))
        else:
            excess = effective_daily - rules.room_rent_limit_per_day
            results.append(ValidationResult(
                rule="room_rent",
                status="FAIL",
                reason=f"Room charges ₹{effective_daily:.0f}/day exceed the policy limit of ₹{rules.room_rent_limit_per_day:.0f}/day by ₹{excess:.0f}/day.",
                amount=excess,
            ))
    else:
        results.append(ValidationResult(
            rule="room_rent",
            status="PASS",
            reason="No room rent limit specified in policy.",
            amount=0,
        ))

    # ---- 2. Exclusions Check ----
    diagnosis = (claim.medical.primary_diagnosis or "").lower()
    procedure = (claim.medical.procedure or "").lower()
    excluded_match = None

    for exclusion in rules.exclusions:
        excl_lower = exclusion.lower()
        if excl_lower in diagnosis or excl_lower in procedure:
            excluded_match = exclusion
            break

    if excluded_match:
        results.append(ValidationResult(
            rule="exclusions",
            status="FAIL",
            reason=f"The diagnosis/procedure matches a policy exclusion: '{excluded_match}'.",
            amount=0,
        ))
    else:
        results.append(ValidationResult(
            rule="exclusions",
            status="PASS",
            reason="Diagnosis and procedure are not on the exclusion list.",
            amount=0,
        ))

    # ---- 3. Co-pay Calculation ----
    if rules.copay_percentage > 0:
        total_bill = claim.billing.total_bill
        patient_copay = total_bill * (rules.copay_percentage / 100)
        insurer_share = total_bill - patient_copay

        results.append(ValidationResult(
            rule="copay",
            status="WARNING",
            reason=f"Policy has a {rules.copay_percentage:.0f}% co-pay. Patient pays ₹{patient_copay:.0f}, insurer pays ₹{insurer_share:.0f} of the ₹{total_bill:.0f} total.",
            amount=patient_copay,
        ))
    else:
        results.append(ValidationResult(
            rule="copay",
            status="PASS",
            reason="No co-pay required under this policy.",
            amount=0,
        ))

    # ---- 4. ICU Sub-limit Check ----
    if rules.sub_limits.icu > 0 and claim.billing.icu_charges > 0:
        if claim.billing.icu_charges <= rules.sub_limits.icu:
            results.append(ValidationResult(
                rule="icu_sublimit",
                status="PASS",
                reason=f"ICU charges ₹{claim.billing.icu_charges:.0f} are within the sub-limit of ₹{rules.sub_limits.icu:.0f}.",
                amount=claim.billing.icu_charges,
            ))
        else:
            excess = claim.billing.icu_charges - rules.sub_limits.icu
            results.append(ValidationResult(
                rule="icu_sublimit",
                status="FAIL",
                reason=f"ICU charges ₹{claim.billing.icu_charges:.0f} exceed the sub-limit of ₹{rules.sub_limits.icu:.0f} by ₹{excess:.0f}.",
                amount=excess,
            ))

    # ---- 5. OT Sub-limit Check ----
    if rules.sub_limits.ot > 0 and claim.billing.ot_charges > 0:
        if claim.billing.ot_charges <= rules.sub_limits.ot:
            results.append(ValidationResult(
                rule="ot_sublimit",
                status="PASS",
                reason=f"OT charges ₹{claim.billing.ot_charges:.0f} are within the sub-limit of ₹{rules.sub_limits.ot:.0f}.",
                amount=claim.billing.ot_charges,
            ))
        else:
            excess = claim.billing.ot_charges - rules.sub_limits.ot
            results.append(ValidationResult(
                rule="ot_sublimit",
                status="FAIL",
                reason=f"OT charges ₹{claim.billing.ot_charges:.0f} exceed the sub-limit of ₹{rules.sub_limits.ot:.0f} by ₹{excess:.0f}.",
                amount=excess,
            ))

    # ---- 6. Pre-authorization Check ----
    if rules.pre_auth_required:
        if claim.insurance.pre_auth_number:
            results.append(ValidationResult(
                rule="pre_auth",
                status="PASS",
                reason=f"Pre-authorization obtained: {claim.insurance.pre_auth_number}.",
                amount=0,
            ))
        else:
            results.append(ValidationResult(
                rule="pre_auth",
                status="FAIL",
                reason="Policy requires pre-authorization but no pre-auth number was provided.",
                amount=0,
            ))
    else:
        results.append(ValidationResult(
            rule="pre_auth",
            status="PASS",
            reason="Pre-authorization is not required for this policy.",
            amount=0,
        ))

    # ---- 7. Sum Insured Check ----
    if rules.sum_insured > 0:
        if claim.billing.total_bill <= rules.sum_insured:
            results.append(ValidationResult(
                rule="sum_insured",
                status="PASS",
                reason=f"Total bill ₹{claim.billing.total_bill:.0f} is within the sum insured of ₹{rules.sum_insured:.0f}.",
                amount=claim.billing.total_bill,
            ))
        else:
            excess = claim.billing.total_bill - rules.sum_insured
            results.append(ValidationResult(
                rule="sum_insured",
                status="FAIL",
                reason=f"Total bill ₹{claim.billing.total_bill:.0f} exceeds the sum insured of ₹{rules.sum_insured:.0f} by ₹{excess:.0f}.",
                amount=excess,
            ))

    # ---- 8. Document Completeness (basic check) ----
    missing_docs = []
    if not claim.documents.hospital_bill:
        missing_docs.append("hospital bill")
    if not claim.documents.discharge_summary:
        missing_docs.append("discharge summary")
    if not claim.documents.id_proof:
        missing_docs.append("ID proof")

    if missing_docs:
        results.append(ValidationResult(
            rule="documents",
            status="WARNING",
            reason=f"Missing documents: {', '.join(missing_docs)}. These are typically required for claim processing.",
            amount=0,
        ))
    else:
        results.append(ValidationResult(
            rule="documents",
            status="PASS",
            reason="All basic required documents are present.",
            amount=0,
        ))

    # Log summary
    pass_count = sum(1 for r in results if r.status == "PASS")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    warn_count = sum(1 for r in results if r.status == "WARNING")
    logger.info(
        "Step 2 complete — %d PASS, %d FAIL, %d WARNING (total %d rules)",
        pass_count, fail_count, warn_count, len(results),
    )

    return results


# ---------------------------------------------------------------------------
# Step 3: Coverage Summary Generation (LLM)
# ---------------------------------------------------------------------------

def generate_coverage_summary(
    claim: ClaimSchema,
    results: List[ValidationResult],
) -> str:
    """
    Generate a plain English coverage summary using LLM.

    Explains validation results in simple language that patients
    and hospital staff can understand. Uses rupee amounts.

    Args:
        claim: The claim being validated.
        results: Validation results from Step 2.

    Returns:
        Plain English coverage summary string.
    """
    logger.info("Step 3: Generating coverage summary with LLM")

    # Format validation results for the prompt
    results_text = "\n".join(
        f"- {r.rule}: {r.status} — {r.reason}" for r in results
    )

    # Build compact claim summary
    claim_summary = (
        f"Patient: {claim.patient.name or 'Unknown'}\n"
        f"Diagnosis: {claim.medical.primary_diagnosis or 'Unknown'}\n"
        f"Procedure: {claim.medical.procedure or 'Unknown'}\n"
        f"Total Bill: ₹{claim.billing.total_bill:.0f}\n"
        f"Hospital: {claim.hospital.name or 'Unknown'}\n"
        f"Admission: {claim.admission.admission_type or 'Unknown'} "
        f"({claim.admission.length_of_stay} days)"
    )

    prompt = COVERAGE_SUMMARY_PROMPT.format(
        validation_results=results_text,
        claim_summary=claim_summary,
    )

    summary = call_llm(prompt=prompt, system=COVERAGE_SUMMARY_SYSTEM)
    logger.info("Step 3 complete — summary length=%d", len(summary))
    return summary.strip()


# ---------------------------------------------------------------------------
# Public API: Full M2 Pipeline
# ---------------------------------------------------------------------------

def validate_claim(
    claim: ClaimSchema,
    policy_rules: Optional[PolicyRules] = None,
    policy_pdf_bytes: Optional[bytes] = None,
    policy_text: Optional[str] = None,
    skip_summary: bool = False,
) -> dict:
    """
    Full M2 Pipeline — validate a claim against its insurance policy.

    Provide policy rules via ONE of:
      - policy_rules: Pre-parsed PolicyRules object (from cache)
      - policy_pdf_bytes: Raw PDF bytes of the policy document
      - policy_text: Extracted text from the policy document

    Args:
        claim: The ClaimSchema to validate.
        policy_rules: Pre-parsed policy rules (skips Step 1).
        policy_pdf_bytes: Policy PDF bytes (triggers Step 1 parsing).
        policy_text: Policy text (triggers Step 1 parsing).
        skip_summary: If True, skip the LLM summary (Step 3).

    Returns:
        Dict with:
          - "validation_results": List of validation result dicts
          - "coverage_summary": Plain English summary (or None if skipped)
          - "policy_rules": Parsed policy rules dict
          - "validated_claim": Updated claim dict with status
          - "overall_status": "PASS", "FAIL", or "WARNING"
    """
    logger.info("=" * 50)
    logger.info("M2 Policy Engine starting | claim_id=%s", claim.claim_id)

    # --- Step 1: Get or parse policy rules ---
    if policy_rules is None:
        if policy_pdf_bytes:
            policy_rules = parse_policy_from_pdf(policy_pdf_bytes)
        elif policy_text:
            policy_rules = parse_policy_from_text(policy_text)
        else:
            raise ValueError(
                "Must provide one of: policy_rules, policy_pdf_bytes, or policy_text"
            )

    # --- Step 2: Deterministic validation ---
    results = validate_claim_against_policy(claim, policy_rules)

    # --- Step 3: Coverage summary ---
    coverage_summary = None
    if not skip_summary:
        try:
            coverage_summary = generate_coverage_summary(claim, results)
        except Exception as e:
            logger.error("Coverage summary generation failed: %s", str(e))
            coverage_summary = (
                "Unable to generate coverage summary. "
                "Please review the validation results above."
            )

    # Determine overall status
    has_fail = any(r.status == "FAIL" for r in results)
    has_warn = any(r.status == "WARNING" for r in results)

    if has_fail:
        overall = "FAIL"
        claim_status = "Incomplete Claim"
    elif has_warn:
        overall = "WARNING"
        claim_status = "Validated with Warnings"
    else:
        overall = "PASS"
        claim_status = "Validated"

    # Update claim status
    validated_claim = claim.model_copy(deep=True)
    validated_claim.meta.status = claim_status

    logger.info("M2 complete | overall=%s | status=%s", overall, claim_status)
    logger.info("=" * 50)

    return {
        "validation_results": [r.model_dump() for r in results],
        "coverage_summary": coverage_summary,
        "policy_rules": policy_rules.model_dump(),
        "validated_claim": validated_claim.model_dump(),
        "overall_status": overall,
    }


def validate_claim_with_mock_policy(claim: ClaimSchema) -> dict:
    """
    Validate a claim using a hardcoded demo policy (no LLM needed).

    Useful for testing or when no policy PDF is available.
    Skips Step 1 (LLM parsing) and Step 3 (LLM summary).
    """
    demo_rules = PolicyRules(
        policy_id="DEMO-POLICY-001",
        insurer="Demo Health Insurance",
        room_rent_limit_per_day=5000,
        waiting_period_days=30,
        exclusions=["dental", "cosmetic surgery", "maternity"],
        copay_percentage=10,
        sub_limits=PolicySubLimits(icu=10000, ot=8000),
        cashless_eligible=True,
        reimbursement_eligible=True,
        pre_auth_required=True,
        sum_insured=500000,
        network_hospitals_only=False,
    )

    return validate_claim(
        claim=claim,
        policy_rules=demo_rules,
        skip_summary=True,
    )
