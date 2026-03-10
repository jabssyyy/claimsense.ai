"""
ClaimSense.ai - OCR Service

Thin wrapper around pytesseract for Tesseract OCR (Tier 3)
and Gemini Vision OCR (Tier 4) for handwriting, low-quality scans.
"""

import io
import logging
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)


def ocr_available() -> bool:
    """Check if Tesseract OCR is installed and accessible."""
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        logger.info("Tesseract OCR available: version %s", version)
        return True
    except Exception as e:
        logger.warning(
            "Tesseract OCR not available: %s. "
            "Tier 3 OCR will be skipped. Install Tesseract to enable OCR.",
            str(e),
        )
        return False


def ocr_image(image: Image.Image) -> Tuple[str, float]:
    """
    Run Tesseract OCR on a PIL Image.

    Returns:
        Tuple of (extracted_text, confidence_score 0.0-1.0).
    """
    import pytesseract
    import pandas as pd

    try:
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DATAFRAME,
            lang="eng",
        )
        text_data = data[data["conf"] != -1]

        if text_data.empty:
            logger.warning("OCR produced no text from image")
            return ("", 0.0)

        mean_confidence = text_data["conf"].mean() / 100.0
        words = text_data["text"].dropna().astype(str).tolist()
        text = " ".join(w for w in words if w.strip())

        logger.info("OCR completed | words=%d | confidence=%.2f", len(words), mean_confidence)
        return (text, mean_confidence)

    except Exception as e:
        logger.error("OCR failed: %s", str(e))
        return ("", 0.0)


def ocr_image_simple(image: Image.Image) -> str:
    """Simple OCR - returns just the text without confidence score."""
    import pytesseract

    try:
        text = pytesseract.image_to_string(image, lang="eng")
        return text.strip()
    except Exception as e:
        logger.error("Simple OCR failed: %s", str(e))
        return ""


def gemini_vision_ocr(images: list) -> Tuple[str, float]:
    """
    Tier 4 - Gemini Vision OCR.

    Sends page images to Gemini Vision to extract text.
    Handles handwritten documents, low quality scans, and regional languages.

    Args:
        images: List of PIL Images (one per PDF page).

    Returns:
        Tuple of (extracted_text, confidence_score).
    """
    from services.llm_service import call_llm_vision

    if not images:
        return ("", 0.0)

    logger.info("Gemini Vision OCR starting | pages=%d", len(images))

    try:
        image_bytes_list = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            image_bytes_list.append(buf.getvalue())

        prompt = (
            "Extract ALL text from this document image. This may contain "
            "handwritten text, low quality scans, or text in regional Indian "
            "languages (Hindi, Tamil, Telugu, Kannada, etc.). "
            "Return ONLY the extracted text, preserving the original layout "
            "as closely as possible. If text is unclear, provide your best "
            "interpretation with [unclear] markers."
        )

        result = call_llm_vision(
            prompt=prompt,
            images=image_bytes_list,
            system="You are a document OCR specialist. Extract text accurately.",
        )

        if result and result.strip():
            logger.info("Gemini Vision OCR succeeded | chars=%d", len(result))
            return (result.strip(), 0.92)

        logger.warning("Gemini Vision OCR returned empty result")
        return ("", 0.0)

    except Exception as e:
        logger.error("Gemini Vision OCR failed: %s", str(e))
        return ("", 0.0)


# Backward-compatible alias
def cloud_ocr_placeholder(file_bytes: bytes) -> Tuple[str, float]:
    """Legacy alias. Use gemini_vision_ocr() instead."""
    logger.warning("cloud_ocr_placeholder called - use gemini_vision_ocr() instead")
    return ("", 0.0)
