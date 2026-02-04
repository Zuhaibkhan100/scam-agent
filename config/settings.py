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
    # Recommended:
    # - gemini-1.5-flash (fast, cheap)
    # - gemini-1.5-pro (strong reasoning)
    LLM_MODEL_NAME: str = os.getenv(
        "LLM_MODEL_NAME",
        "gemini-2.5-flash-lite"
    )

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
        os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "10")
    )

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


# --------------------------------------------------
# Singleton settings object
# --------------------------------------------------
settings = Settings()
