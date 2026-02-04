from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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

_GENAI_CONFIGURED = False
_GEMINI_MODELS: dict[str, Any] = {}

_GEMINI_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if not t.startswith("```"):
        return t

    # Remove surrounding fences.
    t = t.strip("`").strip()
    if t.lower().startswith("json"):
        t = t[4:].strip()
    return t


def _extract_json_object(text: str) -> str | None:
    t = _strip_code_fences(text)
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return t[start : end + 1]


def _parse_json_object(text: str) -> dict[str, Any] | None:
    candidate = _extract_json_object(text)
    if not candidate:
        return None
    try:
        obj = json.loads(candidate)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _generate_content_with_timeout(model: Any, prompt: str) -> Any | None:
    """
    Best-effort timeout wrapper around `model.generate_content`.
    Returns None on timeout/failure.
    """
    timeout_s = float(getattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 10))
    if timeout_s <= 0:
        timeout_s = 10

    future = _GEMINI_EXECUTOR.submit(model.generate_content, prompt)
    try:
        return future.result(timeout=timeout_s)
    except FuturesTimeoutError:
        return None


def _gemini_enabled() -> bool:
    return (settings.LLM_PROVIDER or "").strip().lower() == "gemini"


def _ensure_gemini_model(model_name: str | None = None) -> Any | None:
    """
    Lazy-init Gemini model. Never raises.
    """
    global _GENAI_CONFIGURED, _GEMINI_MODELS

    if not _gemini_enabled():
        return None

    if not settings.GEMINI_API_KEY:
        return None

    name = (model_name or settings.LLM_MODEL_NAME or "").strip()
    if not name:
        return None
    if not name.startswith("models/"):
        name = f"models/{name}"

    if name in _GEMINI_MODELS:
        return _GEMINI_MODELS[name]

    try:
        import google.generativeai as genai  # type: ignore

        if not _GENAI_CONFIGURED:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            _GENAI_CONFIGURED = True

        model = genai.GenerativeModel(name)
        _GEMINI_MODELS[name] = model
        return model
    except Exception:
        return None


def _model_name_candidates() -> list[str]:
    names: list[str] = []
    primary = (settings.LLM_MODEL_NAME or "").strip()
    if primary:
        if not primary.startswith("models/"):
            primary = f"models/{primary}"
        names.append(primary)
    for n in getattr(settings, "LLM_FALLBACK_MODEL_NAMES", []) or []:
        s = str(n or "").strip()
        if s and s not in names:
            if not s.startswith("models/"):
                s = f"models/{s}"
            names.append(s)
    return names


def _is_retryable_gemini_error(exc: Exception) -> bool:
    msg = str(exc or "")
    ml = msg.lower()
    return (
        " 429 " in f" {msg} "
        or "quota exceeded" in ml
        or "rate limit" in ml
        or "retry_delay" in ml
        or "resource has been exhausted" in ml
        or " 404 " in f" {msg} "
        or "not found" in ml
        or "not supported" in ml
    )


def _generate_with_fallback_models(prompt: str) -> Any | None:
    last_error: Exception | None = None
    for name in _model_name_candidates():
        model = _ensure_gemini_model(name)
        if model is None:
            continue
        try:
            response = _generate_content_with_timeout(model, prompt)
            if response is None:
                last_error = TimeoutError(f"Gemini request timed out for model {name}.")
                continue
            return response
        except Exception as e:
            last_error = e
            if _is_retryable_gemini_error(e):
                continue
            raise
    if last_error:
        raise last_error
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
    has_phone = bool(re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", t))
    has_credentials = any(k in tl for k in ["otp", "one time password", "pin", "cvv", "password"])

    has_urgency = any(k in tl for k in ["urgent", "immediately", "today", "asap", "right away", "act now", "within"])
    has_threat = any(k in tl for k in ["blocked", "suspended", "freeze", "closed", "limited", "deactivated"])
    has_verification = any(
        k in tl
        for k in [
            "verify",
            "verification",
            "verify now",
            "verify immediately",
            "kyc",
            "update kyc",
            "update",
            "confirm",
            "click",
            "login",
        ]
    )
    has_financial = any(k in tl for k in ["bank", "account", "upi", "card", "payment", "wallet"])
    has_reward = any(k in tl for k in ["refund", "cashback", "prize", "won", "offer"])
    has_payment_action = any(k in tl for k in ["share your upi", "upi id", "collect request", "transfer", "send money", "pay now"])

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
    if has_phone:
        score += 0.25
        indicators.append("contains a phone number")

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
    if has_payment_action:
        score += 0.25
        indicators.append("payment redirection")

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

    Note: when `LLM_STRICT=true`, this function may raise instead of falling back.
    """
    global _LAST_CALL_TS_CLASSIFIER

    strict = bool(getattr(settings, "LLM_STRICT", False))

    # Deterministic fallback (used when strict mode is disabled).
    fallback_text = _extract_text_from_classifier_prompt(prompt)
    fallback = _heuristic_classify(fallback_text)

    if not _gemini_enabled() or not settings.GEMINI_API_KEY:
        if strict:
            raise RuntimeError("Gemini is not configured (LLM_PROVIDER=gemini + GEMINI_API_KEY required).")
        return fallback

    now = time.time()
    if settings.LLM_COOLDOWN_SECONDS > 0 and now - _LAST_CALL_TS_CLASSIFIER < settings.LLM_COOLDOWN_SECONDS:
        # Respect cooldown by waiting (keeps outputs AI-generated instead of falling back).
        time.sleep(max(0.0, settings.LLM_COOLDOWN_SECONDS - (now - _LAST_CALL_TS_CLASSIFIER)))
        now = time.time()

    try:
        response = _generate_with_fallback_models(prompt)
        if response is None:
            if strict:
                raise TimeoutError("Gemini request timed out.")
            return fallback
        _LAST_CALL_TS_CLASSIFIER = now

        raw_text = (response.text or "").strip()
        result = _parse_json_object(raw_text)
        if result is None:
            raise ValueError("Failed to parse JSON from Gemini classifier output.")
        scam = bool(result.get("scam", False))
        confidence = float(result.get("confidence", fallback["confidence"]))
        confidence = max(0.0, min(confidence, 1.0))
        reason = str(result.get("reason", fallback["reason"]))

        return {"scam": scam, "confidence": confidence, "reason": reason}

    except Exception as e:
        if strict:
            raise
        print(f"Gemini classifier error: {e}")
        return fallback


def call_llm_for_json(prompt: str, *, retries: int = 1) -> dict[str, Any] | None:
    """
    JSON-only generation helper.
    Returns a dict or None (when strict mode is disabled).
    When `LLM_STRICT=true`, this function may raise on failures/timeouts.
    """
    strict = bool(getattr(settings, "LLM_STRICT", False))
    if not _gemini_enabled() or not settings.GEMINI_API_KEY:
        if strict:
            raise RuntimeError("Gemini is not configured (LLM_PROVIDER=gemini + GEMINI_API_KEY required).")
        return None

    # Reuse the reply cooldown bucket (this is typically called for "generation"-type tasks).
    global _LAST_CALL_TS_REPLY
    now = time.time()
    if settings.LLM_COOLDOWN_SECONDS > 0 and now - _LAST_CALL_TS_REPLY < settings.LLM_COOLDOWN_SECONDS:
        time.sleep(max(0.0, settings.LLM_COOLDOWN_SECONDS - (now - _LAST_CALL_TS_REPLY)))
        now = time.time()

    try:
        response = _generate_with_fallback_models(prompt)
    except Exception as e:
        if strict:
            raise
        print(f"Gemini JSON error: {e}")
        return None
    if response is None:
        if strict:
            raise TimeoutError("Gemini request timed out.")
        return None
    _LAST_CALL_TS_REPLY = now

    raw_text = (response.text or "").strip()
    parsed = _parse_json_object(raw_text)
    if parsed is not None:
        return parsed

    if retries <= 0:
        if strict:
            raise ValueError("Failed to parse JSON from Gemini output.")
        return None

    repair_prompt = (
        "Return ONLY a valid JSON object. Do not include markdown, code fences, or extra text.\n\n"
        f"Previous output:\n{raw_text}"
    )
    return call_llm_for_json(repair_prompt, retries=retries - 1)


def call_llm_for_reply(prompt: str) -> str:
    """
    Plain-text generation used for victim replies and (optionally) analyst summaries.
    In non-strict mode, never raises and falls back to a safe string.
    When `LLM_STRICT=true`, this function may raise on failures/timeouts.
    """
    global _LAST_CALL_TS_REPLY

    strict = bool(getattr(settings, "LLM_STRICT", False))
    if not _gemini_enabled() or not settings.GEMINI_API_KEY:
        if strict:
            raise RuntimeError("Gemini is not configured (LLM_PROVIDER=gemini + GEMINI_API_KEY required).")
        return (
            "I'm not comfortable sharing any details over messages. "
            "Can you send the official link or contact number so I can verify?"
        )
    now = time.time()

    if settings.LLM_COOLDOWN_SECONDS > 0 and now - _LAST_CALL_TS_REPLY < settings.LLM_COOLDOWN_SECONDS:
        # Wait instead of returning a deterministic line.
        time.sleep(max(0.0, settings.LLM_COOLDOWN_SECONDS - (now - _LAST_CALL_TS_REPLY)))
        now = time.time()

    try:
        response = _generate_with_fallback_models(prompt)
        if response is None:
            if strict:
                raise TimeoutError("Gemini request timed out.")
            return (
                "Sorry, I'm not sure I understand. "
                "Can you share the official link or contact number so I can verify?"
            )
        _LAST_CALL_TS_REPLY = now

        reply = (response.text or "").strip()
        if not reply:
            if strict:
                raise ValueError("Empty reply from Gemini.")
            return (
                "Sorry, I'm not sure I understand. "
                "Can you share the official link or number so I can check?"
            )
        return reply

    except Exception as e:
        if strict:
            raise
        print(f"Gemini reply error: {e}")
        return (
            "Sorry, I'm not sure I understand. "
            "Can you share the official link or contact number so I can verify?"
        )
