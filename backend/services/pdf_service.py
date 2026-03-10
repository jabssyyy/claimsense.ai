"""
ClaimSense.ai - PDF Service

Extracts text from PDF documents.

Tier 2: Uses PyPDF2 to read embedded text layers from digitally-created PDFs.
If the PDF is scanned (no text layer), converts pages to images for OCR (Tier 3/4).
"""

import hashlib
import logging
from pathlib import Path
from typing import Tuple, List

from PIL import Image

logger = logging.getLogger(__name__)


def compute_file_hash(file_bytes: bytes) -> str:
    """
    Compute SHA-256 hash of file contents.
    Used by Tier 1 (Metadata Gate) for duplicate detection.
    """
    return hashlib.sha256(file_bytes).hexdigest()


def is_pdf_blank(file_bytes: bytes) -> bool:
    """
    Check if a PDF file is blank or corrupted.

    Returns True if the PDF has zero pages or cannot be read at all.
    """
    try:
        from PyPDF2 import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(file_bytes))
        if len(reader.pages) == 0:
            logger.warning("PDF has zero pages — blank file")
            return True
        return False
    except Exception as e:
        logger.error("PDF appears corrupted or unreadable: %s", str(e))
        return True


def is_pdf_encrypted(file_bytes: bytes) -> bool:
    """
    Check if a PDF is password-protected.

    Returns True if the PDF is encrypted and cannot be read without a password.
    """
    try:
        from PyPDF2 import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(file_bytes))
        return reader.is_encrypted
    except Exception:
        return False


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, int]:
    """
    Tier 2 — Extract embedded text from a PDF using PyPDF2.

    Digitally created PDFs (not scans) have a text layer that can be read
    directly without OCR. This is free and fast.

    Args:
        file_bytes: Raw PDF file bytes.

    Returns:
        Tuple of (extracted_text, page_count).
        extracted_text will be empty string if no text layer exists.
    """
    from PyPDF2 import PdfReader
    from io import BytesIO

    try:
        reader = PdfReader(BytesIO(file_bytes))
        page_count = len(reader.pages)
        text_parts = []

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
                logger.debug("Page %d: extracted %d chars", i + 1, len(page_text))
            else:
                logger.debug("Page %d: no text layer", i + 1)

        full_text = "\n\n".join(text_parts)
        logger.info(
            "PDF text extraction | pages=%d | text_length=%d | has_text=%s",
            page_count,
            len(full_text),
            bool(full_text.strip()),
        )
        return (full_text.strip(), page_count)

    except Exception as e:
        logger.error("PDF text extraction failed: %s", str(e))
        return ("", 0)


def pdf_pages_to_images(file_bytes: bytes) -> List[Image.Image]:
    """
    Convert PDF pages to PIL Images for OCR processing.

    Uses pdf2image (which requires poppler installed on the system).
    Falls back to a warning if poppler is not available.

    Args:
        file_bytes: Raw PDF file bytes.

    Returns:
        List of PIL Images, one per page.
    """
    try:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(file_bytes, dpi=300)
        logger.info("Converted PDF to %d images for OCR", len(images))
        return images

    except ImportError:
        logger.error(
            "pdf2image is not installed. Run: pip install pdf2image"
        )
        return []
    except Exception as e:
        logger.error(
            "PDF to image conversion failed: %s. "
            "Make sure poppler is installed: "
            "Windows: download from https://github.com/oschwartz10612/poppler-windows/releases | "
            "Ubuntu: sudo apt install poppler-utils | "
            "Mac: brew install poppler",
            str(e),
        )
        return []
