"""
ClaimSense.ai - Standard Claim JSON Schema

THIS IS THE BACKBONE OF THE ENTIRE SYSTEM.
M1 produces this. M2 and M3 consume it. Every module speaks this language.

DO NOT change field names without updating all three modules AND the frontend.

Built for the Indian market:
- INR (rupees) for all amounts
- ABHA ID for patient health identification
- Indian TPA names (Medi Assist, MDIndia, Star Health, HDFC Ergo)
- ICD-10 codes following Indian coding conventions
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Nested sub-models
# ---------------------------------------------------------------------------

class PatientInfo(BaseModel):
    """Patient demographic and insurance information."""
    name: Optional[str] = None
    dob: Optional[str] = None                # Date string (flexible format from LLM)
    gender: Optional[str] = None
    abha_id: Optional[str] = None            # Ayushman Bharat Health Account ID (XX-XXXX-XXXX-XXXX)
    phone: Optional[str] = None
    email: Optional[str] = None
    policy_number: Optional[str] = None


class HospitalInfo(BaseModel):
    """Hospital and treating physician details."""
    hospital_id: Optional[str] = None
    name: Optional[str] = None
    doctor_name: Optional[str] = None
    department: Optional[str] = None
    staff_name: Optional[str] = None
    tpa_name: Optional[str] = None           # Third Party Administrator


class AdmissionInfo(BaseModel):
    """Admission and stay details."""
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    admission_type: Optional[str] = None     # Emergency, Planned, Day Care
    ward_type: Optional[str] = None          # General, Semi-Private, Private, ICU
    room_type: Optional[str] = None          # Single, Shared, Suite
    length_of_stay: int = 0

    @field_validator("length_of_stay", mode="before")
    @classmethod
    def parse_length_of_stay(cls, v):
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            # Extract leading digits from strings like "4 Days", "3 days", "4"
            m = re.match(r"(\d+)", v.strip())
            return int(m.group(1)) if m else 0
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0


class MedicalInfo(BaseModel):
    """Diagnosis and procedure information."""
    primary_diagnosis: Optional[str] = None
    icd10_code: Optional[str] = None         # e.g. I10, J18.9
    secondary_diagnosis: Optional[str] = None
    secondary_icd10: Optional[str] = None
    procedure: Optional[str] = None
    procedure_code: Optional[str] = None     # e.g. PROC-2001


class BillingInfo(BaseModel):
    """Itemized billing in INR (Indian Rupees)."""
    room_charges: float = 0.0
    icu_charges: float = 0.0
    doctor_fees: float = 0.0
    ot_charges: float = 0.0                  # Operation Theatre charges
    medicines: float = 0.0
    lab_charges: float = 0.0
    other_charges: float = 0.0
    total_bill: float = 0.0
    pre_auth_amount: float = 0.0


class DocumentsInfo(BaseModel):
    """Document availability flags. True = document is present."""
    hospital_bill: bool = False
    discharge_summary: bool = False
    prescription: bool = False
    lab_reports: bool = False
    pre_auth_letter: bool = False
    id_proof: bool = False


class InsuranceInfo(BaseModel):
    """Insurance and pre-authorization details."""
    insurer_name: Optional[str] = None
    pre_auth_number: Optional[str] = None


class MetaInfo(BaseModel):
    """Claim processing metadata."""
    status: str = "Draft"                    # Draft, Extracted, Validated, Ready for Submission, Submitted, Hold
    submitted_at: Optional[str] = None       # ISO 8601 timestamp


# ---------------------------------------------------------------------------
# Top-level claim schema
# ---------------------------------------------------------------------------

class ClaimSchema(BaseModel):
    """
    The standard claim JSON schema for ClaimSense.ai.

    This is the universal data contract across all modules:
    - M1 (DocTriage) produces this from uploaded documents
    - M2 (Policy Engine) validates this against policy rules
    - M3 (Clean Claim) performs final checks and builds submission package
    - Frontend displays this as readable cards

    Example claim_id format: CLM-2026-001
    """
    claim_id: Optional[str] = None
    input_type: Optional[str] = "PDF"        # "PDF" or "Structured"
    patient: PatientInfo = Field(default_factory=PatientInfo)
    hospital: HospitalInfo = Field(default_factory=HospitalInfo)
    admission: AdmissionInfo = Field(default_factory=AdmissionInfo)
    medical: MedicalInfo = Field(default_factory=MedicalInfo)
    billing: BillingInfo = Field(default_factory=BillingInfo)
    documents: DocumentsInfo = Field(default_factory=DocumentsInfo)
    insurance: InsuranceInfo = Field(default_factory=InsuranceInfo)
    meta: MetaInfo = Field(default_factory=MetaInfo)


# ---------------------------------------------------------------------------
# Policy rules schema (used by M2 - cached per policy)
# ---------------------------------------------------------------------------

class PolicySubLimits(BaseModel):
    """Sub-limits for specific charge categories in INR."""
    icu: float = 0.0
    ot: float = 0.0


class PolicyRules(BaseModel):
    """
    Parsed insurance policy rules (extracted by LLM, cached per policy).

    M2 Step 1 produces this. M2 Step 2 consumes it for deterministic validation.
    The LLM parses a policy document ONCE. This cache is reused for all claims
    under the same policy.
    """
    policy_id: Optional[str] = None
    insurer: Optional[str] = None
    room_rent_limit_per_day: float = 0.0
    waiting_period_days: int = 0
    exclusions: list[str] = Field(default_factory=list)
    copay_percentage: float = 0.0
    sub_limits: PolicySubLimits = Field(default_factory=PolicySubLimits)
    cashless_eligible: bool = True
    reimbursement_eligible: bool = True
    pre_auth_required: bool = True
    sum_insured: float = 0.0
    network_hospitals_only: bool = False


# ---------------------------------------------------------------------------
# Validation result schema (used by M2 and M3)
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    """Result of a single policy rule check."""
    rule: str                                # e.g. "room_rent", "exclusions", "pre_auth"
    status: str                              # "PASS", "FAIL", or "WARNING"
    reason: str                              # Human-readable explanation
    amount: float = 0.0                      # Relevant amount in INR (if applicable)


# ---------------------------------------------------------------------------
# Submission package schema (used by M3)
# ---------------------------------------------------------------------------

class MissingItem(BaseModel):
    """A single missing document or issue found during M3 checks."""
    item_type: str                           # "document", "code", "mismatch"
    item_name: str                           # e.g. "id_proof", "icd10_code"
    description: str                         # Human-readable description of what's missing/wrong


class SubmissionPackage(BaseModel):
    """
    Final submission package produced by M3 (Clean Claim Guarantee).

    Contains the validated claim, all check results, and submission status.
    """
    claim: ClaimSchema = Field(default_factory=ClaimSchema)
    validation_results: list[ValidationResult] = Field(default_factory=list)
    coverage_summary: Optional[str] = None
    code_check_results: list[ValidationResult] = Field(default_factory=list)
    document_check_results: list[ValidationResult] = Field(default_factory=list)
    missing_items: list[MissingItem] = Field(default_factory=list)
    status: str = "Hold - Action Required"   # "Ready for Submission" or "Hold - Action Required"
    claim_reference: Optional[str] = None    # Generated on successful submission
    fhir_payload: Optional[dict] = None      # FHIR-compliant JSON for insurer API
