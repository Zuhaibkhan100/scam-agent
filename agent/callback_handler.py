import requests
import json
from config.settings import settings


def send_final_callback(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    extracted_intelligence: dict,
    agent_notes: str
) -> bool:
    """
    Send final intelligence callback to GUVI evaluation endpoint.
    
    Returns True if successful, False otherwise.
    """
    if not settings.CALLBACK_ENABLED:
        return False

    payload = {
        "sessionId": session_id,
        "scamDetected": scam_detected,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": {
            "bankAccounts": extracted_intelligence.get("bankAccounts", []),
            "upiIds": extracted_intelligence.get("upiIds", []),
            "phishingLinks": extracted_intelligence.get("phishingLinks", []),
            "phoneNumbers": extracted_intelligence.get("phoneNumbers", []),
            "suspiciousKeywords": extracted_intelligence.get("suspiciousKeywords", []),
        },
        "agentNotes": agent_notes,
    }

    try:
        response = requests.post(
            settings.CALLBACK_URL,
            json=payload,
            timeout=5
        )
        return response.status_code in (200, 201, 202)
    except Exception as e:
        print(f"Callback failed for session {session_id}: {str(e)}")
        return False


def should_finalize_engagement(
    total_messages: int,
    confidence: float,
    intel_signals: int
) -> bool:
    """
    Heuristic to decide if engagement is sufficient for final callback.
    
    Returns True if:
    - At least CALLBACK_MIN_TURNS messages exchanged AND
    - (High confidence OR extracted at least 1 intelligence signal)
    """
    if total_messages < settings.CALLBACK_MIN_TURNS:
        return False

    # High confidence scam detection
    if confidence > 0.85:
        return True

    # Or extracted meaningful intelligence
    if intel_signals >= 1:
        return True

    return False
