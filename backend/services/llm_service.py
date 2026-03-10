"""
ClaimSense.ai - LLM Service

CRITICAL: This is the SINGLE abstraction for ALL LLM calls in the entire system.
Every module (M1, M2, M3) must call call_llm() or call_llm_vision() from here.
NEVER call Gemini directly anywhere else in the codebase.

To switch from Gemini to another model (Claude, GPT, etc.):
Change ONLY _get_client() and the API calls inside call_llm() / call_llm_vision().
Every caller stays the same.
"""

import json
import logging
import re

from google import genai
from google.genai import types

from config import get_settings

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    """
    Create and return a Gemini client.
    Validates that the API key is configured.
    """
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Get a key at https://aistudio.google.com/apikey "
            "and add it to backend/.env"
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _parse_json_response(raw: str) -> dict:
    """
    Strip markdown code fences and parse raw LLM text as JSON.

    Shared helper used by call_llm_json() and call_llm_vision_json().
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse LLM response as JSON | error=%s | response=%.500s",
            str(e),
            raw,
        )
        raise


def call_llm(prompt: str, system: str = "") -> str:
    """
    Single abstraction for all text-only LLM calls in ClaimSense.ai.

    Args:
        prompt: The user/task prompt to send to the model.
        system: Optional system instruction to guide model behavior.

    Returns:
        The model's text response as a string.

    Raises:
        ValueError: If GEMINI_API_KEY is not configured.
        Exception: If the API call fails (logged with details).
    """
    settings = get_settings()
    model = settings.GEMINI_MODEL

    logger.info("LLM call starting | model=%s | prompt_length=%d", model, len(prompt))
    if system:
        logger.debug("System instruction: %.200s", system)
    logger.debug("Prompt (first 500 chars): %.500s", prompt)

    try:
        client = _get_client()

        # Configure generation parameters
        config = types.GenerateContentConfig(
            temperature=0.1,           # Low temperature for deterministic extraction
            max_output_tokens=4096,
        )
        if system:
            config.system_instruction = system

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        result = response.text
        logger.info("LLM call succeeded | response_length=%d", len(result))
        logger.debug("Response (first 500 chars): %.500s", result)
        return result

    except Exception as e:
        logger.error(
            "LLM call failed | error=%s | type=%s",
            str(e),
            type(e).__name__,
        )
        raise


def call_llm_json(prompt: str, system: str = "") -> dict:
    """
    Call the LLM and parse the response as JSON.

    Convenience wrapper around call_llm() that strips markdown code fences
    and parses the response as JSON.
    """
    raw = call_llm(prompt, system)
    return _parse_json_response(raw)


def call_llm_vision(
    prompt: str,
    images: list[bytes],
    system: str = "",
    mime_type: str = "image/png",
) -> str:
    """
    Multimodal LLM call -- send text + images to Gemini Vision.

    Args:
        prompt: The text prompt describing what to extract/analyze.
        images: List of image byte arrays (PNG or JPEG).
        system: Optional system instruction.
        mime_type: MIME type of all images (default "image/png").

    Returns:
        The model's text response as a string.
    """
    settings = get_settings()
    model = settings.GEMINI_MODEL

    logger.info(
        "LLM vision call starting | model=%s | images=%d | prompt_length=%d",
        model, len(images), len(prompt),
    )

    try:
        client = _get_client()

        config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=4096,
        )
        if system:
            config.system_instruction = system

        # Build multimodal contents: text prompt + image parts
        contents = [prompt]
        for img_bytes in images:
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        result = response.text
        logger.info("LLM vision call succeeded | response_length=%d", len(result))
        return result

    except Exception as e:
        logger.error(
            "LLM vision call failed | error=%s | type=%s",
            str(e),
            type(e).__name__,
        )
        raise


def call_llm_vision_json(
    prompt: str,
    images: list[bytes],
    system: str = "",
    mime_type: str = "image/png",
) -> dict:
    """
    Multimodal LLM call that returns parsed JSON.

    Combines call_llm_vision() + JSON parsing.
    """
    raw = call_llm_vision(prompt, images, system, mime_type)
    return _parse_json_response(raw)
