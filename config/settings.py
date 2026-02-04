import os
from dotenv import load_dotenv

# --------------------------------------------------
# Load environment variables ONCE
# --------------------------------------------------
load_dotenv()


class Settings:
    """
    Centralized configuration.
    This file must NOT import any logic or SDK modules.
    """

    # ---------------------------
    # LLM Provider Configuration
    # ---------------------------

    # Gemini API key
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # API key for endpoint auth
    API_KEY: str = os.getenv("API_KEY", "")

    # Gemini model name
    # Correct options:
    # - gemini-1.5-flash (fast, cheap) ✅ RECOMMENDED
    # - gemini-1.5-pro (strong reasoning)
    LLM_MODEL_NAME: str = os.getenv(
        "LLM_MODEL_NAME",
        "gemini-1.5-flash"  # Fixed: was gemini-flash-latest (invalid)
    )

    # Optional model fallbacks (comma-separated). Used if the primary model hits free-tier quota/rate limits.
    # Example: "gemini-1.5-flash,gemini-1.5-flash-8b"
    _LLM_FALLBACK_MODEL_NAMES_RAW: str = os.getenv(
        "LLM_FALLBACK_MODEL_NAMES",
        "gemini-2.5-flash,gemma-3-4b-it",
    )
    LLM_FALLBACK_MODEL_NAMES: list[str] = [
        x.strip() for x in _LLM_FALLBACK_MODEL_NAMES_RAW.split(",") if x.strip()
    ]

    # Optional: provider name (useful later for switching)
    LLM_PROVIDER: str = os.getenv(
        "LLM_PROVIDER",
        "mock"
    )

    # ---------------------------
    # Rate limiting / safety
    # ---------------------------

    # Cooldown between LLM calls (seconds)
    # Important for free-tier safety
    LLM_COOLDOWN_SECONDS: int = int(
        os.getenv("LLM_COOLDOWN_SECONDS", "2")
    )

    # Hard timeout for any single LLM request (seconds).
    # If exceeded, the API will fall back to deterministic heuristics/text.
    LLM_REQUEST_TIMEOUT_SECONDS: float = float(
        os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "5")  # Reduced from 10 to 5
    )

    # If enabled, the API will NOT use deterministic/mock fallbacks when Gemini fails.
    # This can increase errors/timeouts on free tiers but guarantees "AI-only" behavior.
    LLM_STRICT: bool = os.getenv("LLM_STRICT", "false").lower() in ("1", "true", "yes", "on")

    # ---------------------------
    # Fallback behavior
    # ---------------------------

    # Default confidence when AI fails
    DEFAULT_CONFIDENCE_ON_FAILURE: float = float(
        os.getenv("DEFAULT_CONFIDENCE_ON_FAILURE", "0.5")
    )

    # ---------------------------
    # Callback to evaluation platform (required for scoring)
    # ---------------------------
    CALLBACK_URL: str = os.getenv(
        "CALLBACK_URL",
        "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    )
    CALLBACK_ENABLED: bool = os.getenv("CALLBACK_ENABLED", "true").lower() in ("1", "true", "yes", "on")
    CALLBACK_MIN_TURNS: int = int(os.getenv("CALLBACK_MIN_TURNS", "2"))
    CALLBACK_DRY_RUN: bool = os.getenv("CALLBACK_DRY_RUN", "false").lower() in ("1", "true", "yes", "on")


# --------------------------------------------------
# Singleton settings object
# --------------------------------------------------
settings = Settings()
