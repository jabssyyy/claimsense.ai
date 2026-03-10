"""
ClaimSense.ai - Upload Routes (M1 DocTriage)

API endpoints for document upload and extraction.

POST /upload-document   — Upload a PDF/image file (Path A)
POST /upload-structured — Submit structured JSON directly (Path B)
"""

import logging
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from config import get_settings
from modules.m1_doctriage import process_pdf_document, process_structured_input

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


# ---------------------------------------------------------------------------
# POST /upload-document — PDF upload (Path A)
# ---------------------------------------------------------------------------

@router.post("/upload-document", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF or image document for M1 DocTriage processing.

    The document goes through 4 tiers:
    1. Metadata Gate (duplicate, blank, encrypted checks)
    2. Text Layer extraction (digital PDFs)
    3. Tesseract OCR (scanned documents)
    4. Cloud OCR (handwriting, low quality — placeholder)

    Extracted text is then sent to Gemini for structured extraction
    into the standard claim JSON schema.

    Returns the extracted ClaimSchema JSON.
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

    # Process through M1 pipeline
    result = process_pdf_document(file_bytes=file_bytes, filename=filename)

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "Document processing failed"),
        )

    return UploadResponse(
        success=True,
        claim=result["claim"],
        extraction_text_length=result.get("extraction_text_length"),
    )


# ---------------------------------------------------------------------------
# POST /upload-structured — Structured JSON input (Path B)
# ---------------------------------------------------------------------------

@router.post("/upload-structured", response_model=UploadResponse)
async def upload_structured(data: StructuredClaimInput):
    """
    Submit a structured claim directly as JSON (Path B).

    No OCR or LLM needed — hospital sends data directly.
    Parses into the standard claim JSON schema.

    Returns the parsed ClaimSchema JSON.
    """
    logger.info("Structured input received")

    result = process_structured_input(data.model_dump())

    return UploadResponse(
        success=True,
        claim=result["claim"],
    )
