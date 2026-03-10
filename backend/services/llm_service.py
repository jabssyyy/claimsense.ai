"""
ClaimSense.ai - LLM Service

CRITICAL: This is the SINGLE abstraction for ALL LLM calls in the entire system.
Every module (M1, M2, M3) must call call_llm() from here.
NEVER call Gemini directly anywhere else in the codebase.

To switch from Gemini to another model (Claude, GPT, etc.):
Change ONLY _get_client() and the API call inside call_llm().
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


def call_llm(prompt: str, system: str = "") -> str:
    """
    Single abstraction for all LLM calls in ClaimSense.ai.

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
    and parses the response as JSON. Useful for M1 extraction and M2 policy
    parsing where the LLM is instructed to return only JSON.

    Args:
        prompt: The user/task prompt (should instruct the LLM to return JSON).
        system: Optional system instruction.

    Returns:
        Parsed JSON as a Python dict.

    Raises:
        json.JSONDecodeError: If the response cannot be parsed as JSON.
    """
    raw = call_llm(prompt, system)

    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (with optional language tag)
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        # Remove closing fence
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
