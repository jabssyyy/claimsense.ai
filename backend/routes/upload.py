"""
ClaimSense.ai - Upload Routes (M1 DocTriage)

API endpoints for document upload and extraction.

POST /upload-document   — Upload a single PDF/image file (Path A)
POST /upload-multiple   — Upload multiple files, merge into one claim
POST /upload-structured — Submit structured JSON directly (Path B)
"""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from config import get_settings
from modules.m1_doctriage import process_pdf_document, process_image_document, process_structured_input

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class StructuredClaimInput(BaseModel):
    """Request body for structured (JSON) claim input — Path B."""
    patient: dict = {}
    hospital: dict = {}
    admission: dict = {}
    medical: dict = {}
    billing: dict = {}
    documents: dict = {}
    insurance: dict = {}


class UploadResponse(BaseModel):
    """Response from both upload endpoints."""
    success: bool
    claim: dict | None = None
    error: str | None = None
    extraction_text_length: int | None = None
    fraud_detection: dict | None = None


# ---------------------------------------------------------------------------
# POST /upload-document — Single file upload (Path A)
# ---------------------------------------------------------------------------

@router.post("/upload-document", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF or image document for M1 DocTriage processing.
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/tiff",
    ]
    content_type = file.content_type or ""
    filename = file.filename or "unknown"

    logger.info(
        "Upload received | filename=%s | content_type=%s",
        filename, content_type,
    )

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. "
                   f"Accepted types: PDF, PNG, JPEG, TIFF",
        )

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Save file to uploads directory
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / filename

    with open(save_path, "wb") as f:
        f.write(file_bytes)
    logger.info("File saved to %s (%d bytes)", save_path, len(file_bytes))

    # Process through M1 pipeline - route PDFs vs images separately
    if content_type == "application/pdf":
        result = process_pdf_document(file_bytes=file_bytes, filename=filename)
    else:
        result = process_image_document(file_bytes=file_bytes, filename=filename)

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "Document processing failed"),
        )

    return UploadResponse(
        success=True,
        claim=result["claim"],
        extraction_text_length=result.get("extraction_text_length"),
        fraud_detection=result.get("fraud_detection"),
    )


# ---------------------------------------------------------------------------
# POST /upload-multiple — Multiple files merged into one claim
# ---------------------------------------------------------------------------

def _merge_claims(base: dict, new: dict) -> dict:
    """
    Merge two claim dicts. Non-null/non-default values from 'new'
    override values in 'base'. Works recursively for nested dicts.
    """
    for key, value in new.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge_claims(base[key], value)
        elif value is not None and value != "" and value != 0 and value != 0.0 and value is not False:
            base[key] = value
    return base


@router.post("/upload-multiple", response_model=UploadResponse)
async def upload_multiple(files: List[UploadFile] = File(...)):
    """
    Upload multiple files (PDFs + images) and merge extracted data
    into a single unified claim. Each file is processed through M1
    independently, then all extracted fields are merged together.
    """
    allowed_types = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/tiff",
    ]

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    logger.info("Multi-file upload received | count=%d", len(files))

    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    merged_claim = None
    total_text_length = 0
    fraud_results = []
    errors = []

    for file in files:
        content_type = file.content_type or ""
        filename = file.filename or "unknown"

        if content_type not in allowed_types:
            errors.append(f"Skipped {filename}: unsupported type {content_type}")
            continue

        file_bytes = await file.read()
        if len(file_bytes) == 0:
            errors.append(f"Skipped {filename}: empty file")
            continue

        # Save file
        save_path = upload_dir / filename
        with open(save_path, "wb") as f:
            f.write(file_bytes)
        logger.info("Multi-upload: saved %s (%d bytes)", filename, len(file_bytes))

        # Process through M1
        if content_type == "application/pdf":
            result = process_pdf_document(file_bytes=file_bytes, filename=filename)
        else:
            result = process_image_document(file_bytes=file_bytes, filename=filename)

        if not result["success"]:
            errors.append(f"{filename}: {result.get('error', 'processing failed')}")
            continue

        # Merge into combined claim
        if merged_claim is None:
            merged_claim = result["claim"]
        else:
            _merge_claims(merged_claim, result["claim"])

        total_text_length += result.get("extraction_text_length", 0)

        if result.get("fraud_detection"):
            fraud_results.append(result["fraud_detection"])

    if merged_claim is None:
        raise HTTPException(
            status_code=422,
            detail=f"No files could be processed. Errors: {'; '.join(errors)}" if errors else "All files failed processing.",
        )

    # Combine fraud results (take highest risk)
    combined_fraud = None
    if fraud_results:
        combined_fraud = max(fraud_results, key=lambda f: f.get("risk_score", 0))

    return UploadResponse(
        success=True,
        claim=merged_claim,
        extraction_text_length=total_text_length,
        fraud_detection=combined_fraud,
    )


# ---------------------------------------------------------------------------
# POST /upload-structured — Structured JSON input (Path B)
# ---------------------------------------------------------------------------

@router.post("/upload-structured", response_model=UploadResponse)
async def upload_structured(data: StructuredClaimInput):
    """
    Submit a structured claim directly as JSON (Path B).
    No OCR or LLM needed — hospital sends data directly.
    """
    logger.info("Structured input received")

    result = process_structured_input(data.model_dump())

    return UploadResponse(
        success=True,
        claim=result["claim"],
    )
