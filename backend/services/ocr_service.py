"""
ClaimSense.ai - OCR Service

Thin wrapper around pytesseract for Tesseract OCR (Tier 3)
and a placeholder for Cloud OCR (Tier 4 - Google Cloud Vision).

Tier 3: Local Tesseract OCR - free, handles most scanned documents.
Tier 4: Cloud OCR - placeholder for handwriting, low-quality scans, regional languages.
"""

import logging
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


def ocr_available() -> bool:
    """
    Check if Tesseract OCR is installed and accessible.

    Returns True if Tesseract can be reached, False otherwise.
    Called during startup to log OCR capability status.
    """
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        logger.info("Tesseract OCR available: version %s", version)
        return True
    except Exception as e:
        logger.warning(
            "Tesseract OCR not available: %s. "
            "Tier 3 OCR will be skipped. Install Tesseract to enable OCR: "
            "Windows: download from https://github.com/UB-Mannheim/tesseract/wiki | "
            "Ubuntu: sudo apt install tesseract-ocr | "
            "Mac: brew install tesseract",
            str(e),
        )
        return False


def ocr_image(image: Image.Image) -> Tuple[str, float]:
    """
    Run Tesseract OCR on a PIL Image.

    Args:
        image: PIL Image to OCR.

    Returns:
        Tuple of (extracted_text, confidence_score).
        Confidence is 0.0-1.0 where 1.0 is perfect.
    """
    import pytesseract
    import pandas as pd

    try:
        # Get detailed OCR data including confidence scores
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DATAFRAME,
            lang="eng",
        )

        # Filter out non-text entries (conf == -1)
        text_data = data[data["conf"] != -1]

        if text_data.empty:
            logger.warning("OCR produced no text from image")
            return ("", 0.0)

        # Calculate mean confidence (Tesseract gives 0-100, normalize to 0-1)
        mean_confidence = text_data["conf"].mean() / 100.0

        # Join all recognized text
        words = text_data["text"].dropna().astype(str).tolist()
        text = " ".join(w for w in words if w.strip())

        logger.info(
            "OCR completed | words=%d | confidence=%.2f",
            len(words),
            mean_confidence,
        )
        return (text, mean_confidence)

    except Exception as e:
        logger.error("OCR failed: %s", str(e))
        return ("", 0.0)


def ocr_image_simple(image: Image.Image) -> str:
    """
    Simple OCR - returns just the text without confidence score.
    Fallback when detailed data is not needed.
    """
    import pytesseract

    try:
        text = pytesseract.image_to_string(image, lang="eng")
        return text.strip()
    except Exception as e:
        logger.error("Simple OCR failed: %s", str(e))
        return ""


def cloud_ocr_placeholder(file_bytes: bytes) -> Tuple[str, float]:
    """
    Tier 4 - Cloud OCR placeholder.

    This would call Google Cloud Vision or AWS Textract for:
    - Handwritten documents
    - Low quality scans (confidence < 85% from Tesseract)
    - Regional language text (Hindi, Tamil, etc.)

    For MVP: returns empty result with a log message.
    Integration point for production: replace this function body.
    """
    logger.warning(
        "Cloud OCR (Tier 4) not yet integrated. "
        "Document requires cloud-based OCR processing. "
        "For production, integrate Google Cloud Vision or AWS Textract here."
    )
    return ("", 0.0)
