import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from config.settings import settings

# --------------------------------------------------
# Environment & Model Setup
# --------------------------------------------------
load_dotenv()

if not settings.GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment")

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel(settings.LLM_MODEL_NAME)

# --------------------------------------------------
# Rate-limit protection (free tier safety)
# --------------------------------------------------
_LAST_CALL_TS_CLASSIFIER = 0
_LAST_CALL_TS_REPLY = 0


# --------------------------------------------------
# Core LLM call (robust + safe)
# --------------------------------------------------
def call_llm(prompt: str) -> dict:
    """
    Calls the LLM and returns a structured response.

    Guaranteed return format:
    {
        "scam": bool,
        "confidence": float (0.0–1.0),
        "reason": str
    }

    Never raises exceptions.
    """
    global _LAST_CALL_TS_CLASSIFIER

    now = time.time()
    if now - _LAST_CALL_TS_CLASSIFIER < settings.LLM_COOLDOWN_SECONDS:
        return {
            "scam": False,
            "confidence": settings.DEFAULT_CONFIDENCE_ON_FAILURE,
            "reason": "LLM cooldown active; analysis deferred"
        }

    try:
        response = model.generate_content(prompt)
        _LAST_CALL_TS_CLASSIFIER = now

        raw_text = response.text.strip()

        # -------------------------------
        # Sanitize LLM output
        # -------------------------------
        # Remove markdown code fences
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()

        # Extract JSON object only
        start = raw_text.find("{")
        end = raw_text.rfind("}")

        if start != -1 and end != -1 and end > start:
            raw_text = raw_text[start:end + 1]

        result = json.loads(raw_text)

        return {
            "scam": bool(result.get("scam", False)),
            "confidence": float(result.get("confidence", settings.DEFAULT_CONFIDENCE_ON_FAILURE)),
            "reason": result.get("reason", "")
        }

    except ResourceExhausted:
        return {
            "scam": False,
            "confidence": settings.DEFAULT_CONFIDENCE_ON_FAILURE,
            "reason": "LLM quota exceeded; analysis unavailable"
        }

    except Exception as e:
        return {
            "scam": False,
            "confidence": settings.DEFAULT_CONFIDENCE_ON_FAILURE,
            "reason": f"LLM error: {str(e)}"
        }


# --------------------------------------------------
# LLM call for plain text replies (Stage-2, Stage-3)
# --------------------------------------------------
def call_llm_for_reply(prompt: str) -> str:
    """
    Calls the LLM and returns plain text response (no JSON parsing).
    Used for victim agent replies and analyst summaries.

    Guaranteed return:
    - Non-empty string on success
    - Static fallback string on failure

    Never raises exceptions.
    """
    global _LAST_CALL_TS_REPLY

    now = time.time()
    if now - _LAST_CALL_TS_REPLY < settings.LLM_COOLDOWN_SECONDS:
        return "System is in cooldown. Please try again later."

    try:
        response = model.generate_content(prompt)
        _LAST_CALL_TS_REPLY = now

        reply = response.text.strip()
        if not reply:
            return "I'm not sure how to respond. Can you provide more details?"
        
        return reply

    except ResourceExhausted:
        return "Service quota exceeded. Please try again later."

    except Exception as e:
        return f"Unable to generate reply at this time."
