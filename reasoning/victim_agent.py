from reasoning.llm_client import call_llm_for_reply
from config.settings import settings
from extraction.extractor import extract_intelligence

PASSIVE_FALLBACK_REPLY = (
    "Sorry, I'm having trouble understanding. Can you explain again?"
)


def _mock_reply(last_message: str, agent_mode: str, memory: list | None, risk: float | None) -> str:
    """
    Deterministic fallback for LLM_PROVIDER=mock.
    Keeps a human tone while trying to extract actionable scam intelligence.
    """
    # Low-risk: stay generic to avoid overfitting or "investigative" language.
    if risk is None or risk < 0.6:
        if agent_mode == "stall":
            return "Okay. Can you tell me what this is regarding?"
        return "Sorry, I'm not sure I understand. What is this regarding?"

    scammer_only = []
    if memory:
        scammer_only = [str(t.get("content", "")) for t in memory[-6:] if t.get("role") == "scammer"]

    all_text = " ".join([t for t in (scammer_only + [last_message or ""]) if t]).strip()
    intel = extract_intelligence(all_text)

    has_link = bool(intel.get("urls"))
    has_phone = bool(intel.get("phone_numbers"))
    has_email = bool(intel.get("emails"))
    has_upi = bool(intel.get("upi_ids"))

    if not has_link:
        ask = "Can you send me the official website link you're asking me to use?"
    elif not has_phone:
        ask = "What's the official helpline number I should call to verify this?"
    elif not has_email:
        ask = "Can you share the official email address for this so I can cross-check?"
    elif not has_upi and any(k in all_text.lower() for k in ["upi", "payment", "pay"]):
        ask = "Which UPI ID should I be checking this against?"
    else:
        ask = "Do you have a reference ID or ticket number for this?"

    if agent_mode == "stall":
        prefix = "Okay, give me a moment."
    elif agent_mode == "escalate":
        prefix = "I can't share any details over messages."
    else:
        prefix = "Sorry, I'm a bit confused."

    return f"{prefix} {ask}"


def generate_passive_reply(
    last_message: str,
    conversation_id: str = None,
    risk: float = None,
    agent_mode: str = "confused",
    memory: list = None
) -> dict:
    """
    Generate a passive, human-like reply to a scammer message.

    Returns:
    {
        'reply': str,
        'fallback': bool,
        'reason': str | None
    }
    """

    # If we're not using Gemini, stay deterministic but still extraction-oriented.
    use_gemini = (settings.LLM_PROVIDER or "").strip().lower() == "gemini" and bool(settings.GEMINI_API_KEY)
    if not use_gemini:
        return {
            "reply": _mock_reply(last_message=last_message, agent_mode=agent_mode, memory=memory, risk=risk),
            "fallback": True,
            "reason": "LLM_PROVIDER=mock",
        }

    # ---------------------------------------------
    # Build conversation history (memory injection)
    # ---------------------------------------------
    history_text = ""

    if memory:
        # Only inject last N turns to avoid prompt bloat
        for turn in memory[-6:]:
            role = "Scammer" if turn["role"] == "scammer" else "You"
            history_text += f"{role}: {turn['content']}\n"

    # ---------------------------------------------
    # Build dynamic prompt
    # ---------------------------------------------
    extraction_guidance = ""
    if risk is not None and risk >= 0.6:
        extraction_guidance = """
Goal (high-risk): keep them talking and politely ask for details that help you "verify",
like the official website/link, UPI/payment ID, bank account number, phone number, or email.
Do NOT provide any personal or banking details yourself.
"""

    prompt = f"""
You are a cautious, slightly confused human.
You are not sure if the other person is legitimate.
Your goal is to keep the conversation going without giving
any personal, banking, or verification details.

Conversation so far:
{history_text if history_text else "(no prior context)"}

Latest message from the other person:
"{last_message}"

Behavior mode: {agent_mode}

Instructions:
- Sound natural and human
- Ask for clarification if unsure
- If you made a mistake earlier, correct yourself naturally
- Never use words like "scam", "fraud", "phishing", or "suspicious"
- Do NOT accuse
- Do NOT warn
- Do NOT provide sensitive information
{extraction_guidance}
"""

    try:
        reply = call_llm_for_reply(prompt)

        if not reply or not isinstance(reply, str) or not reply.strip():
            raise ValueError("Empty reply from LLM")

        reply = reply.strip()
        if (reply.startswith('"') and reply.endswith('"')) or (reply.startswith("'") and reply.endswith("'")):
            reply = reply[1:-1].strip()

        # Guardrail: never reveal detection in the outgoing message.
        banned = ["scam", "scammer", "fraud", "phishing", "suspicious"]
        if any(b in reply.lower() for b in banned):
            return {
                "reply": (
                    "I'm not comfortable sharing any details over messages. "
                    "Can you send the official link or contact number so I can verify?"
                ),
                "fallback": True,
                "reason": "Detected disallowed wording in model reply",
            }

        return {
            "reply": reply,
            "fallback": False,
            "reason": None
        }

    except Exception:
        # Safe fallback that still fits the persona
        return {
            "reply": PASSIVE_FALLBACK_REPLY,
            "fallback": True,
            "reason": "LLM unavailable, fallback reply used"
        }
