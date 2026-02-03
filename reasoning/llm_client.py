from __future__ import annotations

import json
import re
import time
from typing import Any

from dotenv import load_dotenv

from config.settings import settings

# --------------------------------------------------
# Environment
# --------------------------------------------------
load_dotenv()

_LAST_CALL_TS_CLASSIFIER = 0.0
_LAST_CALL_TS_REPLY = 0.0

_GEMINI_MODEL: Any | None = None
_GEMINI_INIT_ATTEMPTED = False


def _gemini_enabled() -> bool:
    return (settings.LLM_PROVIDER or "").strip().lower() == "gemini"


def _ensure_gemini_model() -> Any | None:
    """
    Lazy-init Gemini model. Never raises.
    """
    global _GEMINI_MODEL, _GEMINI_INIT_ATTEMPTED

    if not _gemini_enabled():
        return None

    if _GEMINI_INIT_ATTEMPTED:
        return _GEMINI_MODEL
    _GEMINI_INIT_ATTEMPTED = True

    if not settings.GEMINI_API_KEY:
        return None

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=settings.GEMINI_API_KEY)
        _GEMINI_MODEL = genai.GenerativeModel(settings.LLM_MODEL_NAME)
        return _GEMINI_MODEL
    except Exception:
        _GEMINI_MODEL = None
        return None


def _extract_text_from_classifier_prompt(prompt: str) -> str:
    """
    The classifier prompt always embeds the message inside a triple-quoted block.
    This is used to provide heuristic fallbacks when no LLM is available.
    """
    m = re.search(r'Message:\s*"""(.*?)"""', prompt, flags=re.S)
    if m:
        return m.group(1).strip()

    blocks = re.findall(r'"""(.*?)"""', prompt, flags=re.S)
    if blocks:
        return blocks[-1].strip()

    return ""


def _heuristic_classify(text: str) -> dict[str, Any]:
    """
    Returns a best-effort scam probability using deterministic heuristics.
    The returned confidence is the probability-of-scam in [0,1].
    """
    t = (text or "").strip()
    tl = t.lower()

    if len(tl) < 6:
        return {"scam": False, "confidence": 0.05, "reason": "Message too short to assess reliably."}

    indicators: list[str] = []

    has_link = bool(re.search(r"https?://", tl))
    has_upi = bool(re.search(r"\b[\w.\-]{2,}@[a-zA-Z]{2,}\b", t))  # UPI-like
    has_credentials = any(k in tl for k in ["otp", "one time password", "pin", "cvv", "password"])

    has_urgency = any(k in tl for k in ["urgent", "immediately", "now", "today", "asap", "right away"])
    has_threat = any(k in tl for k in ["blocked", "suspended", "freeze", "closed", "limited", "deactivated"])
    has_verification = any(k in tl for k in ["verify", "verification", "kyc", "update", "confirm", "click", "login"])
    has_financial = any(k in tl for k in ["bank", "account", "upi", "card", "payment", "wallet"])
    has_reward = any(k in tl for k in ["refund", "cashback", "prize", "won", "offer"])

    # Weighted probability score (probability-of-scam)
    score = 0.05

    if has_credentials:
        score += 0.55
        indicators.append("requests sensitive credentials")
    if has_link:
        score += 0.40
        indicators.append("contains a link")
    if has_upi:
        score += 0.40
        indicators.append("contains a payment/UPI id")

    if has_financial:
        score += 0.10
        indicators.append("financial context")
    if has_verification:
        score += 0.25
        indicators.append("verification request")
    if has_threat:
        score += 0.25
        indicators.append("threat of account action")
    if has_urgency:
        score += 0.15
        indicators.append("urgency pressure")
    if has_reward:
        score += 0.15
        indicators.append("reward lure")

    score = max(0.0, min(score, 0.95))

    scam = score >= 0.55

    if indicators:
        reason = "Likely scam: " + ", ".join(indicators[:3]) + "."
    else:
        reason = "No strong scam indicators found in the text."

    return {"scam": scam, "confidence": float(score), "reason": reason}


def call_llm(prompt: str) -> dict[str, Any]:
    """
    Scam classification call.

    Returns:
    {
      "scam": bool,
      "confidence": float (0.0-1.0),
      "reason": str
    }
    """
    global _LAST_CALL_TS_CLASSIFIER

    # Always provide a deterministic fallback (used for mock mode, cooldown, or any failure).
    fallback_text = _extract_text_from_classifier_prompt(prompt)
    fallback = _heuristic_classify(fallback_text)

    # Mock mode: skip any external LLM calls.
    model = _ensure_gemini_model()
    if model is None:
        return fallback

    now = time.time()
    if now - _LAST_CALL_TS_CLASSIFIER < settings.LLM_COOLDOWN_SECONDS:
        return fallback

    try:
        response = model.generate_content(prompt)
        _LAST_CALL_TS_CLASSIFIER = now

        raw_text = (response.text or "").strip()

        # Remove markdown code fences.
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()

        # Extract JSON object only.
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_text = raw_text[start : end + 1]

        result = json.loads(raw_text)
        scam = bool(result.get("scam", False))
        confidence = float(result.get("confidence", fallback["confidence"]))
        confidence = max(0.0, min(confidence, 1.0))
        reason = str(result.get("reason", fallback["reason"]))

        return {"scam": scam, "confidence": confidence, "reason": reason}

    except Exception:
        return fallback


def call_llm_for_reply(prompt: str) -> str:
    """
    Plain-text generation used for victim replies and (optionally) analyst summaries.
    Never raises; always returns a safe human-like string.
    """
    global _LAST_CALL_TS_REPLY

    model = _ensure_gemini_model()
    now = time.time()

    if model is None:
        return (
            "I'm not comfortable sharing any details over messages. "
            "Can you send the official link or contact number so I can verify?"
        )

    if now - _LAST_CALL_TS_REPLY < settings.LLM_COOLDOWN_SECONDS:
        return (
            "Sorry, I'm a bit busy right now. "
            "Can you send the official link or a number to call so I can verify this?"
        )

    try:
        response = model.generate_content(prompt)
        _LAST_CALL_TS_REPLY = now

        reply = (response.text or "").strip()
        if not reply:
            return (
                "Sorry, I'm not sure I understand. "
                "Can you share the official link or number so I can check?"
            )
        return reply

    except Exception:
        return (
            "Sorry, I'm not sure I understand. "
            "Can you share the official link or contact number so I can verify?"
        )
