import json
from typing import Type, TypeVar
from pydantic import BaseModel
from config import settings
from utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class GeminiConfigurationError(Exception):
    """Raised when live Gemini processing is requested without valid credentials."""


def generate_structured_json(
    system_instruction: str,
    user_prompt: str,
    response_schema: Type[T],
) -> T:
    """Calls Google Gemini API and enforces Pydantic structured JSON validation."""
    if not settings.has_live_gemini:
        raise GeminiConfigurationError(
            "GEMINI_API_KEY is not configured in backend/.env. "
            "Configure a valid Google Gemini API key or run in Deterministic Demo Mode."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.1,
            ),
        )
        raw_text = (response.text or "").strip()
        if not raw_text:
            raise ValueError("Empty response received from Gemini model.")
        parsed = json.loads(raw_text)
        return response_schema.model_validate(parsed)
    except GeminiConfigurationError:
        raise
    except Exception as exc:
        logger.error(f"Gemini structured generation failed: {exc}")
        raise RuntimeError(f"Gemini API execution error: {str(exc)}") from exc
