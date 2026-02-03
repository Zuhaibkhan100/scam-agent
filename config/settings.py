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
        "gemini"
    )

    # ---------------------------
    # Rate limiting / safety
    # ---------------------------

    # Cooldown between LLM calls (seconds)
    # Important for free-tier safety
    LLM_COOLDOWN_SECONDS: int = int(
        os.getenv("LLM_COOLDOWN_SECONDS", "2")
    )

    # ---------------------------
    # Fallback behavior
    # ---------------------------

    # Default confidence when AI fails
    DEFAULT_CONFIDENCE_ON_FAILURE: float = float(
        os.getenv("DEFAULT_CONFIDENCE_ON_FAILURE", "0.5")
    )


# --------------------------------------------------
# Singleton settings object
# --------------------------------------------------
settings = Settings()
