"""
ClaimSense.ai - Module 3: Clean Claim Guarantee

Final quality check before the claim goes to the insurer.
Nothing wrong leaves this module.

Three steps:
  Step 1 - Medical Code & Integrity Check: ICD-10 + procedure code validation
  Step 2 - Document Completeness Scan: required docs checklist by claim type
  Step 3 - Final Submission Package Assembly (LLM): FHIR-compliant bundle
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from models.claim_schema import (
    ClaimSchema,
    ValidationResult,
    MissingItem,
    SubmissionPackage,
)
from services.llm_service import call_llm_json

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ICD-10 Code Reference (common codes for Indian medical claims)
# In production this would be a full database lookup.
# ---------------------------------------------------------------------------

ICD10_CODES: Dict[str, str] = {
    # Cardiovascular
    "I10": "Essential (primary) hypertension",
    "I11": "Hypertensive heart disease",
    "I20": "Angina pectoris",
    "I21": "Acute myocardial infarction",
    "I25": "Chronic ischemic heart disease",
    "I50": "Heart failure",
    "I63": "Cerebral infarction",
    "I64": "Stroke, not specified",
    # Respiratory
    "J06": "Acute upper respiratory infections",
    "J18": "Pneumonia, unspecified organism",
    "J18.9": "Pneumonia, unspecified",
    "J44": "Chronic obstructive pulmonary disease",
    "J45": "Asthma",
    # Digestive
    "K35": "Acute appendicitis",
    "K40": "Inguinal hernia",
    "K80": "Cholelithiasis (gallstones)",
    "K81": "Cholecystitis",
    # Diabetes
    "E11": "Type 2 diabetes mellitus",
    "E10": "Type 1 diabetes mellitus",
    # Kidney
    "N17": "Acute kidney failure",
    "N18": "Chronic kidney disease",
    "N20": "Calculus of kidney and ureter",
    # Orthopedic
    "M17": "Osteoarthritis of knee",
    "M54": "Dorsalgia (back pain)",
    "S72": "Fracture of femur",
    "S82": "Fracture of lower leg",
    # Obstetric
    "O80": "Single spontaneous delivery",
    "O82": "Encounter for caesarean delivery",
    # Infectious
    "A09": "Infectious gastroenteritis and colitis",
    "A90": "Dengue fever",
    "A91": "Dengue haemorrhagic fever",
    "B50": "Plasmodium falciparum malaria",
    # Neoplasms
    "C50": "Malignant neoplasm of breast",
    "C34": "Malignant neoplasm of bronchus and lung",
    # Eye
    "H25": "Age-related cataract",
    "H26": "Other cataract",
}

# Department → expected ICD-10 prefixes mapping for cross-check
DEPARTMENT_CODE_MAP: Dict[str, List[str]] = {
    "cardiology": ["I"],
    "pulmonology": ["J"],
    "gastroenterology": ["K"],
    "endocrinology": ["E"],
    "nephrology": ["N"],
    "orthopedics": ["M", "S"],
    "obstetrics": ["O"],
    "oncology": ["C", "D"],
    "ophthalmology": ["H25", "H26", "H"],
    "dermatology": ["L"],
    "neurology": ["G", "I63", "I64"],
    "general medicine": [],  # accepts all
    "general surgery": [],   # accepts all
    "emergency": [],         # accepts all
}


# ---------------------------------------------------------------------------
# Step 1: Medical Code & Integrity Check
# ---------------------------------------------------------------------------

def check_medical_codes(claim: ClaimSchema) -> tuple[List[ValidationResult], List[MissingItem]]:
    """
    Verify ICD-10 and procedure codes for validity and logical consistency.

    Checks:
    1. ICD-10 code exists and is valid
    2. Procedure code is present
    3. Department-diagnosis cross-check (cardiology code shouldn't pair with dermatology)
    4. Suggest corrections for common errors

    Returns:
        Tuple of (validation_results, missing_items)
    """
    logger.info("Step 1: Medical code integrity check")
    results: List[ValidationResult] = []
    missing: List[MissingItem] = []

    icd_code = claim.medical.icd10_code
    diagnosis = claim.medical.primary_diagnosis or ""
    procedure = claim.medical.procedure or ""
    department = (claim.hospital.department or "").lower().strip()

    # ---- ICD-10 Code Validation ----
    if not icd_code:
        results.append(ValidationResult(
            rule="icd10_code",
            status="FAIL",
            reason="No ICD-10 code provided. Every claim requires a valid diagnosis code.",
        ))
        missing.append(MissingItem(
            item_type="code",
            item_name="icd10_code",
            description="ICD-10 diagnosis code is missing. Please provide the correct code.",
        ))
    else:
        # Check exact match or prefix match
        code_upper = icd_code.upper().strip()
        exact_match = code_upper in ICD10_CODES
        prefix_match = any(code_upper.startswith(k) or k.startswith(code_upper) for k in ICD10_CODES)

        if exact_match:
            expected_desc = ICD10_CODES[code_upper]
            results.append(ValidationResult(
                rule="icd10_code",
                status="PASS",
                reason=f"ICD-10 code {code_upper} is valid: {expected_desc}.",
            ))
        elif prefix_match:
            results.append(ValidationResult(
                rule="icd10_code",
                status="WARNING",
                reason=f"ICD-10 code {code_upper} partially matches known codes. Verify the specific sub-code.",
            ))
        else:
            results.append(ValidationResult(
                rule="icd10_code",
                status="WARNING",
                reason=f"ICD-10 code {code_upper} is not in our common codes reference. Please verify manually.",
            ))

    # ---- Procedure Code Check ----
    if not claim.medical.procedure_code:
        results.append(ValidationResult(
            rule="procedure_code",
            status="WARNING",
            reason="No procedure code provided. Consider adding one for faster processing.",
        ))
    else:
        results.append(ValidationResult(
            rule="procedure_code",
            status="PASS",
            reason=f"Procedure code {claim.medical.procedure_code} is present.",
        ))

    # ---- Department-Diagnosis Cross-Check ----
    if icd_code and department and department in DEPARTMENT_CODE_MAP:
        expected_prefixes = DEPARTMENT_CODE_MAP[department]
        if expected_prefixes:  # empty list = accepts all
            code_upper = icd_code.upper().strip()
            matches = any(code_upper.startswith(p) for p in expected_prefixes)

            if matches:
                results.append(ValidationResult(
                    rule="department_match",
                    status="PASS",
                    reason=f"ICD-10 code {code_upper} is consistent with {department} department.",
                ))
            else:
                results.append(ValidationResult(
                    rule="department_match",
                    status="WARNING",
                    reason=(
                        f"ICD-10 code {code_upper} may not match the {department} department. "
                        f"Expected codes starting with: {', '.join(expected_prefixes)}. "
                        "Please verify this is correct."
                    ),
                ))
                missing.append(MissingItem(
                    item_type="mismatch",
                    item_name="department_diagnosis_mismatch",
                    description=f"Diagnosis code {code_upper} doesn't align with {department}. Verify or correct.",
                ))

    logger.info("Step 1 complete — %d code checks performed", len(results))
    return results, missing


# ---------------------------------------------------------------------------
# Step 2: Document Completeness Scan
# ---------------------------------------------------------------------------

def check_document_completeness(claim: ClaimSchema) -> tuple[List[ValidationResult], List[MissingItem]]:
    """
    Generate a checklist of required documents and check availability.

    Required documents vary by claim type:
    - All claims: hospital bill, discharge summary, ID proof
    - Surgical claims: + OT notes (checked via OT charges)
    - ICU claims: + daily ICU notes (checked via ward type)
    - Emergency claims: + emergency admission certificate

    Returns:
        Tuple of (validation_results, missing_items)
    """
    logger.info("Step 2: Document completeness scan")
    results: List[ValidationResult] = []
    missing: List[MissingItem] = []
    docs = claim.documents

    # ---- Universal required documents ----
    universal_docs = {
        "hospital_bill": ("Hospital Bill", docs.hospital_bill),
        "discharge_summary": ("Discharge Summary", docs.discharge_summary),
        "id_proof": ("ID Proof (Aadhaar/PAN/Passport)", docs.id_proof),
    }

    for doc_key, (doc_name, is_present) in universal_docs.items():
        if is_present:
            results.append(ValidationResult(
                rule=f"doc_{doc_key}",
                status="PASS",
                reason=f"{doc_name} is present.",
            ))
        else:
            results.append(ValidationResult(
                rule=f"doc_{doc_key}",
                status="FAIL",
                reason=f"{doc_name} is MISSING. This document is required for all claims.",
            ))
            missing.append(MissingItem(
                item_type="document",
                item_name=doc_key,
                description=f"Please provide: {doc_name}",
            ))

    # ---- Pre-auth letter ----
    if docs.pre_auth_letter:
        results.append(ValidationResult(
            rule="doc_pre_auth_letter",
            status="PASS",
            reason="Pre-authorization letter is present.",
        ))
    else:
        results.append(ValidationResult(
            rule="doc_pre_auth_letter",
            status="WARNING",
            reason="Pre-authorization letter not provided. May be needed if pre-auth was obtained.",
        ))

    # ---- Conditional: Surgical claims (OT charges > 0) ----
    if claim.billing.ot_charges > 0:
        # In MVP, we don't have a separate OT notes field, so just flag it
        results.append(ValidationResult(
            rule="doc_ot_notes",
            status="WARNING",
            reason="This claim has OT charges. Ensure OT notes and anaesthesia records are included.",
        ))

    # ---- Conditional: ICU claims ----
    ward = (claim.admission.ward_type or "").lower()
    if "icu" in ward or claim.billing.icu_charges > 0:
        results.append(ValidationResult(
            rule="doc_icu_notes",
            status="WARNING",
            reason="This is an ICU claim. Ensure daily ICU notes are included with the submission.",
        ))

    # ---- Conditional: Emergency claims ----
    admission_type = (claim.admission.admission_type or "").lower()
    if "emergency" in admission_type:
        results.append(ValidationResult(
            rule="doc_emergency_cert",
            status="WARNING",
            reason="This is an emergency admission. Ensure the emergency admission certificate is included.",
        ))

    # ---- Lab reports ----
    if docs.lab_reports:
        results.append(ValidationResult(
            rule="doc_lab_reports",
            status="PASS",
            reason="Lab reports are present.",
        ))

    # ---- Prescription ----
    if docs.prescription:
        results.append(ValidationResult(
            rule="doc_prescription",
            status="PASS",
            reason="Prescription is present.",
        ))

    passes = sum(1 for r in results if r.status == "PASS")
    fails = sum(1 for r in results if r.status == "FAIL")
    warns = sum(1 for r in results if r.status == "WARNING")
    logger.info(
        "Step 2 complete — %d PASS, %d FAIL, %d WARNING (%d docs checked)",
        passes, fails, warns, len(results),
    )
    return results, missing


# ---------------------------------------------------------------------------
# Step 3: Final Submission Package Assembly
# ---------------------------------------------------------------------------

FHIR_ASSEMBLY_SYSTEM = (
    "You are a medical claims data specialist. "
    "Convert Indian insurance claim data into FHIR-compliant JSON."
)

FHIR_ASSEMBLY_PROMPT = """Convert the following validated Indian medical insurance claim into a
FHIR-compliant JSON payload suitable for submission to an insurer's API.

Use FHIR R4 resource types. Include:
- Patient resource
- Claim resource with diagnosis and procedure references
- Organization resource for the hospital

Use the claim data exactly as provided. Do not add fictional data.
Return ONLY the JSON object.

Claim data:
{claim_json}"""


def build_fhir_payload(claim: ClaimSchema) -> Optional[dict]:
    """
    Build a FHIR-compliant JSON payload using LLM.

    For MVP: attempts LLM-based conversion. Falls back to a simplified
    payload if the LLM call fails.
    """
    import json

    try:
        prompt = FHIR_ASSEMBLY_PROMPT.format(
            claim_json=json.dumps(claim.model_dump(), indent=2, default=str)
        )
        fhir = call_llm_json(prompt=prompt, system=FHIR_ASSEMBLY_SYSTEM)
        logger.info("FHIR payload generated via LLM")
        return fhir
    except Exception as e:
        logger.warning("LLM FHIR generation failed (%s), using simplified payload", str(e))
        # Fallback: simplified FHIR-style payload
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "name": [{"text": claim.patient.name or "Unknown"}],
                        "identifier": [
                            {"system": "ABHA", "value": claim.patient.abha_id or ""},
                            {"system": "policy", "value": claim.patient.policy_number or ""},
                        ],
                    }
                },
                {
                    "resource": {
                        "resourceType": "Claim",
                        "status": "active",
                        "type": {"text": "institutional"},
                        "diagnosis": [
                            {
                                "sequence": 1,
                                "diagnosisCodeableConcept": {
                                    "coding": [
                                        {
                                            "system": "http://hl7.org/fhir/sid/icd-10",
                                            "code": claim.medical.icd10_code or "",
                                            "display": claim.medical.primary_diagnosis or "",
                                        }
                                    ]
                                },
                            }
                        ],
                        "total": {
                            "value": claim.billing.total_bill,
                            "currency": "INR",
                        },
                    }
                },
                {
                    "resource": {
                        "resourceType": "Organization",
                        "name": claim.hospital.name or "Unknown",
                        "identifier": [
                            {"value": claim.hospital.hospital_id or ""}
                        ],
                    }
                },
            ],
        }


def _generate_claim_reference() -> str:
    """Generate a submission reference number."""
    now = datetime.now(timezone.utc)
    short = uuid.uuid4().hex[:6].upper()
    return f"CS-{now.year}-{short}"


# ---------------------------------------------------------------------------
# Public API: Full M3 Pipeline
# ---------------------------------------------------------------------------

def process_submission(
    claim: ClaimSchema,
    validation_results: Optional[List[dict]] = None,
    coverage_summary: Optional[str] = None,
    skip_fhir: bool = False,
) -> dict:
    """
    Full M3 Pipeline — final quality check and submission package assembly.

    Steps:
      1. Medical code & integrity check
      2. Document completeness scan
      3. Submission package assembly (with FHIR payload if not skipped)

    Args:
        claim: The validated ClaimSchema from M2.
        validation_results: M2 validation results to include in the package.
        coverage_summary: M2 coverage summary to include.
        skip_fhir: If True, skip LLM-generated FHIR payload.

    Returns:
        Dict with submission package data.
    """
    logger.info("=" * 50)
    logger.info("M3 Clean Claim starting | claim_id=%s", claim.claim_id)

    # --- Step 1: Medical Code Check ---
    code_results, code_missing = check_medical_codes(claim)

    # --- Step 2: Document Completeness ---
    doc_results, doc_missing = check_document_completeness(claim)

    # Combine all missing items
    all_missing = code_missing + doc_missing

    # --- Step 3: Assembly ---
    # Determine if submission-ready
    has_critical_fail = (
        any(r.status == "FAIL" for r in code_results) or
        any(r.status == "FAIL" for r in doc_results)
    )

    if has_critical_fail or all_missing:
        status = "Hold - Action Required"
        claim_reference = None
    else:
        status = "Ready for Submission"
        claim_reference = _generate_claim_reference()

    # Update claim status
    final_claim = claim.model_copy(deep=True)
    final_claim.meta.status = status

    # Build FHIR payload (only if submission-ready and not skipped)
    fhir_payload = None
    if status == "Ready for Submission" and not skip_fhir:
        fhir_payload = build_fhir_payload(final_claim)

    # Convert validation results from M2 if provided  
    m2_results = []
    if validation_results:
        m2_results = [ValidationResult(**r) if isinstance(r, dict) else r for r in validation_results]

    # Build the package
    package = SubmissionPackage(
        claim=final_claim,
        validation_results=m2_results,
        coverage_summary=coverage_summary,
        code_check_results=code_results,
        document_check_results=doc_results,
        missing_items=all_missing,
        status=status,
        claim_reference=claim_reference,
        fhir_payload=fhir_payload,
    )

    logger.info(
        "M3 complete | status=%s | missing=%d | reference=%s",
        status, len(all_missing), claim_reference or "N/A",
    )
    logger.info("=" * 50)

    return package.model_dump()
