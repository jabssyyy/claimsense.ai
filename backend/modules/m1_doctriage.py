"""
ClaimSense.ai - Module 1: DocTriage Pipeline

Reads uploaded documents and converts them into the standard claim JSON.

Two input paths:
  Path A (PDF): Upload a PDF → 4-tier processing → LLM extraction → ClaimSchema
  Path B (Structured): Hospital sends JSON directly → parse into ClaimSchema

Four processing tiers (PDF path only):
  Tier 1 - Metadata Gate: duplicate check, blank/corrupt, password-protected
  Tier 2 - Text Layer: PyPDF2 direct text extraction (digital PDFs)
  Tier 3 - Standard OCR: Tesseract (scanned documents, confidence >= 85%)
  Tier 4 - Deep Vision: Cloud OCR placeholder (handwriting, low quality)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Set

from models.claim_schema import ClaimSchema
from services.llm_service import call_llm_json
from services.pdf_service import (
    compute_file_hash,
    is_pdf_blank,
    is_pdf_encrypted,
    extract_text_from_pdf,
    pdf_pages_to_images,
)
from services.ocr_service import ocr_available, ocr_image, cloud_ocr_placeholder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory duplicate tracking (production would use a database)
# ---------------------------------------------------------------------------
_seen_hashes: Set[str] = set()


# ---------------------------------------------------------------------------
# LLM Extraction Prompt (from README)
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM = (
    "You are a medical insurance claims data extractor for the Indian market."
)

EXTRACTION_PROMPT_TEMPLATE = """Extract all available information from the following medical document text and
return it as a JSON object matching this exact schema. If a field cannot be found
in the document, use null for strings and 0 for numbers. Do not guess or infer
values that are not present in the document.

Return ONLY the JSON object. No explanation, no markdown, no extra text.

Schema:
{{
  "patient": {{ "name", "dob", "gender", "abha_id", "phone", "email", "policy_number" }},
  "hospital": {{ "hospital_id", "name", "doctor_name", "department", "staff_name", "tpa_name" }},
  "admission": {{ "admission_date", "discharge_date", "admission_type", "ward_type", "room_type", "length_of_stay" }},
  "medical": {{ "primary_diagnosis", "icd10_code", "secondary_diagnosis", "secondary_icd10", "procedure", "procedure_code" }},
  "billing": {{ "room_charges", "icu_charges", "doctor_fees", "ot_charges", "medicines", "lab_charges", "other_charges", "total_bill", "pre_auth_amount" }},
  "documents": {{ "hospital_bill", "discharge_summary", "prescription", "lab_reports", "pre_auth_letter", "id_proof" }},
  "insurance": {{ "insurer_name", "pre_auth_number" }}
}}

Document text:
{document_text}"""


def _generate_claim_id() -> str:
    """Generate a unique claim ID in format CLM-YYYY-NNN."""
    now = datetime.now(timezone.utc)
    short_id = uuid.uuid4().hex[:4].upper()
    return f"CLM-{now.year}-{short_id}"


# ---------------------------------------------------------------------------
# Tier 1: Metadata Gate
# ---------------------------------------------------------------------------
def _tier1_metadata_gate(file_bytes: bytes) -> Optional[str]:
    """
    Tier 1 — Metadata Gate.

    Checks for duplicates, blank/corrupt files, and password protection.

    Returns:
        None if the file passes all checks.
        Error message string if the file should be rejected.
    """
    # Duplicate check
    file_hash = compute_file_hash(file_bytes)
    if file_hash in _seen_hashes:
        return "Duplicate file detected. This document has already been uploaded."
    _seen_hashes.add(file_hash)

    # Blank/corrupt check
    if is_pdf_blank(file_bytes):
        return "File appears blank or corrupted. Cannot process."

    # Password protection check
    if is_pdf_encrypted(file_bytes):
        return "File is password-protected. Please upload an unprotected version."

    logger.info("Tier 1 passed — file is valid (hash=%s...)", file_hash[:12])
    return None


# ---------------------------------------------------------------------------
# Tier 2-4: Text Extraction
# ---------------------------------------------------------------------------
def _extract_text_from_document(file_bytes: bytes, filename: str) -> str:
    """
    Run through Tiers 2-4 to extract text from a PDF.

    Tier 2: PyPDF2 text extraction (digital PDFs)
    Tier 3: Tesseract OCR (scanned documents)
    Tier 4: Cloud OCR placeholder (low-confidence text)

    Returns:
        Extracted text string. May be empty if all tiers fail.
    """
    # --- Tier 2: Text Layer Extraction ---
    text, page_count = extract_text_from_pdf(file_bytes)
    if text and len(text.strip()) > 50:
        logger.info(
            "Tier 2 resolved — direct text extraction (%d chars from %d pages)",
            len(text), page_count,
        )
        return text

    logger.info("Tier 2 insufficient text (%d chars) — escalating to Tier 3 OCR", len(text))

    # --- Tier 3: Tesseract OCR ---
    if not ocr_available():
        logger.warning("Tesseract not available — skipping Tier 3")
    else:
        images = pdf_pages_to_images(file_bytes)
        if images:
            ocr_texts = []
            total_confidence = 0.0

            for i, img in enumerate(images):
                page_text, confidence = ocr_image(img)
                ocr_texts.append(page_text)
                total_confidence += confidence
                logger.info(
                    "Tier 3 OCR page %d | confidence=%.2f | chars=%d",
                    i + 1, confidence, len(page_text),
                )

            avg_confidence = total_confidence / len(images) if images else 0.0
            full_ocr_text = "\n\n".join(t for t in ocr_texts if t.strip())

            if avg_confidence >= 0.85 and full_ocr_text:
                logger.info(
                    "Tier 3 resolved — Tesseract OCR (avg confidence=%.2f, %d chars)",
                    avg_confidence, len(full_ocr_text),
                )
                return full_ocr_text

            # Tier 3 low confidence — escalate to Tier 4
            logger.info(
                "Tier 3 low confidence (%.2f) — escalating to Tier 4",
                avg_confidence,
            )

            # --- Tier 4: Cloud OCR ---
            cloud_text, cloud_conf = cloud_ocr_placeholder(file_bytes)
            if cloud_text:
                logger.info("Tier 4 resolved — cloud OCR (%d chars)", len(cloud_text))
                return cloud_text

            # Tier 4 not available — fall back to whatever Tesseract produced
            if full_ocr_text:
                logger.warning(
                    "Tier 4 unavailable — falling back to Tier 3 result (low confidence)"
                )
                return full_ocr_text

    # All tiers failed to produce text
    logger.error("All extraction tiers failed for file: %s", filename)
    return ""


# ---------------------------------------------------------------------------
# LLM Extraction
# ---------------------------------------------------------------------------
def _extract_claim_with_llm(document_text: str) -> dict:
    """
    Send extracted document text to the LLM for structured extraction.

    Returns:
        Dict matching the ClaimSchema structure.
    """
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(document_text=document_text)

    logger.info("Sending %d chars to LLM for extraction", len(document_text))
    result = call_llm_json(prompt=prompt, system=EXTRACTION_SYSTEM)
    logger.info("LLM extraction complete — got %d top-level keys", len(result))
    return result


# ---------------------------------------------------------------------------
# Public API: Process PDF (Path A)
# ---------------------------------------------------------------------------
def process_pdf_document(
    file_bytes: bytes,
    filename: str,
) -> dict:
    """
    Path A — Process a PDF document through the full DocTriage pipeline.

    Steps:
      1. Tier 1 metadata gate (reject duplicates, blank, encrypted)
      2. Tiers 2-4 text extraction
      3. LLM extraction into ClaimSchema
      4. Return structured claim JSON

    Args:
        file_bytes: Raw PDF file bytes.
        filename: Original filename (for logging).

    Returns:
        Dict with keys:
          - "success": bool
          - "claim": ClaimSchema dict (if success)
          - "error": str (if failed)
          - "tier_used": str describing which tier resolved the text
          - "extraction_text_length": int
    """
    logger.info("=" * 50)
    logger.info("M1 DocTriage starting | file=%s | size=%d bytes", filename, len(file_bytes))

    # --- Tier 1: Metadata Gate ---
    rejection = _tier1_metadata_gate(file_bytes)
    if rejection:
        logger.warning("Tier 1 REJECTED: %s", rejection)
        return {"success": False, "error": rejection}

    # --- Tiers 2-4: Text Extraction ---
    document_text = _extract_text_from_document(file_bytes, filename)

    if not document_text.strip():
        return {
            "success": False,
            "error": (
                "Could not extract any text from this document. "
                "Please ensure the PDF is not blank and try again, "
                "or use the structured input form instead."
            ),
        }

    # --- LLM Extraction ---
    try:
        extracted = _extract_claim_with_llm(document_text)
    except Exception as e:
        logger.error("LLM extraction failed: %s", str(e))
        return {
            "success": False,
            "error": f"AI extraction failed: {str(e)}",
        }

    # --- Build ClaimSchema ---
    claim = ClaimSchema(
        claim_id=_generate_claim_id(),
        input_type="PDF",
        meta={"status": "Extracted", "submitted_at": None},
    )

    # Merge extracted data into claim
    for section in ["patient", "hospital", "admission", "medical", "billing", "documents", "insurance"]:
        if section in extracted and isinstance(extracted[section], dict):
            section_model = getattr(claim, section)
            for key, value in extracted[section].items():
                if hasattr(section_model, key) and value is not None:
                    try:
                        setattr(section_model, key, value)
                    except (ValueError, TypeError) as e:
                        logger.debug("Skipping field %s.%s: %s", section, key, e)

    logger.info("M1 DocTriage complete | claim_id=%s", claim.claim_id)
    logger.info("=" * 50)

    return {
        "success": True,
        "claim": claim.model_dump(),
        "extraction_text_length": len(document_text),
    }


# ---------------------------------------------------------------------------
# Public API: Process Structured Input (Path B)
# ---------------------------------------------------------------------------
def process_structured_input(data: dict) -> dict:
    """
    Path B — Process pre-structured JSON input.

    No OCR or LLM needed. Hospital sends data directly in JSON format.
    Parse it into the standard ClaimSchema.

    Args:
        data: Dict with claim fields (can be partial).

    Returns:
        Dict with keys:
          - "success": bool
          - "claim": ClaimSchema dict
    """
    logger.info("M1 structured input | keys=%s", list(data.keys()))

    claim = ClaimSchema(
        claim_id=_generate_claim_id(),
        input_type="Structured",
        meta={"status": "Extracted", "submitted_at": None},
    )

    # Merge provided data into claim
    for section in ["patient", "hospital", "admission", "medical", "billing", "documents", "insurance"]:
        if section in data and isinstance(data[section], dict):
            section_model = getattr(claim, section)
            for key, value in data[section].items():
                if hasattr(section_model, key) and value is not None:
                    try:
                        setattr(section_model, key, value)
                    except (ValueError, TypeError) as e:
                        logger.debug("Skipping field %s.%s: %s", section, key, e)

    logger.info("M1 structured input complete | claim_id=%s", claim.claim_id)

    return {
        "success": True,
        "claim": claim.model_dump(),
    }
