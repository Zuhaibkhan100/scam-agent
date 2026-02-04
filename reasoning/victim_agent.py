from reasoning.llm_client import call_llm_for_reply
from config.settings import settings
from extraction.extractor import extract_intelligence

PASSIVE_FALLBACK_REPLY = (
    "Sorry, I'm having trouble understanding. Can you explain again?"
)


def _is_greeting(text: str) -> bool:
    tl = (text or "").strip().lower()
    if not tl:
        return False
    greetings = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "how r u",
        "how are u",
        "howru",
        "hru",
    ]
    return any(g in tl for g in greetings) and len(tl.split()) <= 18


def _low_risk_reply(last_message: str, agent_mode: str, memory: list | None) -> str:
    """
    Low-risk replies should still be "agentic":
    - respond naturally to greetings/introductions
    - ask what this is regarding
    - gently steer toward verifiable details without accusing
    """
    tl = (last_message or "").strip().lower()

    mentioned_bank = any(k in tl for k in ["bank", "sbi", "icici", "hdfc", "axis", "kotak"])
    mentioned_support = any(k in tl for k in ["support", "customer care", "helpdesk", "helpline", "service"])
    mentioned_account = "account" in tl

    already_asked_purpose = False
    already_asked_official = False
    if memory:
        for t in memory[-6:]:
            if t.get("role") != "agent":
                continue
            msg = str(t.get("content", "")).lower()
            if "what is this regarding" in msg or "what's this about" in msg:
                already_asked_purpose = True
            if "official" in msg and ("link" in msg or "number" in msg or "helpline" in msg):
                already_asked_official = True

    if agent_mode == "escalate":
        if mentioned_bank or mentioned_account or mentioned_support:
            return (
                "Hi. I can't discuss any account details over messages. "
                "Please share the official helpline number or an official website link so I can verify."
            )
        return "Hi. What is this about?"

    if _is_greeting(last_message):
        if (mentioned_bank or mentioned_account or mentioned_support) and not already_asked_official:
            return (
                "Hi. I'm okay. What is this about? "
                "If it's regarding my bank account, please share the official helpline number or website so I can verify."
            )
        if not already_asked_purpose:
            return "Hi. I'm okay. What is this about?"
        return "Hi. Can you share more details on what this is regarding?"

    if (mentioned_bank or mentioned_account or mentioned_support) and not already_asked_official:
        return (
            "Okay. Which bank is this regarding, and what exactly do you need? "
            "Please share an official helpline number or website link so I can verify first."
        )

    if not already_asked_purpose:
        return "Sorry, I'm not sure I follow. What is this regarding?"

    return "Can you clarify what you need me to do?"


def _mock_reply(last_message: str, agent_mode: str, memory: list | None, risk: float | None) -> str:
    """
    Deterministic fallback for LLM_PROVIDER=mock.
    Keeps a human tone while trying to extract actionable scam intelligence.
    """
    # Low-risk: stay generic to avoid overfitting or "investigative" language.
    if risk is None or risk < 0.6:
        if agent_mode == "stall":
            return _low_risk_reply(last_message=last_message, agent_mode="stall", memory=memory)
        return _low_risk_reply(last_message=last_message, agent_mode=agent_mode, memory=memory)

    asked_link = False
    asked_phone = False
    asked_email = False
    asked_ref = False

    if memory:
        for t in memory[-10:]:
            if t.get("role") != "agent":
                continue
            msg = str(t.get("content", "")).lower()
            if "official website" in msg or "website link" in msg:
                asked_link = True
            if "helpline" in msg or "number i should call" in msg or "contact number" in msg:
                asked_phone = True
            if "official email" in msg or "email address" in msg:
                asked_email = True
            if "reference" in msg or "ticket number" in msg:
                asked_ref = True

    scammer_only = []
    if memory:
        scammer_only = [str(t.get("content", "")) for t in memory[-6:] if t.get("role") == "scammer"]

    all_text = " ".join([t for t in (scammer_only + [last_message or ""]) if t]).strip()
    intel = extract_intelligence(all_text)

    has_link = bool(intel.get("urls"))
    has_phone = bool(intel.get("phone_numbers"))
    has_email = bool(intel.get("emails"))
    has_upi = bool(intel.get("upi_ids"))

    # Rotate questions to keep engagement and avoid repeating the exact same ask.
    if not has_link and not asked_link:
        ask = "Can you send me the official website link you're asking me to use?"
    elif not has_phone and not asked_phone:
        ask = "What's the official helpline number I should call to verify this?"
    elif not has_email and not asked_email:
        ask = "Can you share the official email address for this so I can cross-check?"
    elif not has_upi and any(k in all_text.lower() for k in ["upi", "payment", "pay"]) and not asked_ref:
        ask = "Do you have a reference ID or ticket number for this?"
    else:
        ask = "Can you repeat the exact steps you want me to follow so I don't do it wrong?"

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
    strict = bool(getattr(settings, "LLM_STRICT", False))
    use_gemini = (settings.LLM_PROVIDER or "").strip().lower() == "gemini" and bool(settings.GEMINI_API_KEY)
    if not use_gemini:
        if strict:
            raise RuntimeError("Gemini is required (set LLM_PROVIDER=gemini and GEMINI_API_KEY).")
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
    prompt = f"""
You are a cautious, slightly confused human chatting over SMS.
You are not sure if the other person is legitimate.
Your goal is to keep the conversation going without giving any personal, banking, or verification details.

Conversation so far:
{history_text if history_text else "(no prior context)"}

Latest message:
"{last_message}"

Rules for your reply:
- Sound natural and human (1-2 short sentences)
- Do NOT accuse or warn
- Do NOT use words: scam, scammer, fraud, phishing, suspicious
- Never share OTP, passwords, PIN, CVV, bank details, or any personal info
- If they pressure you to act/verify/pay or mention OTP/links: ask for an official website/link or helpline number to verify
- If it's just a greeting/intro: respond politely and ask what this is about and which bank/service they mean
""".strip()

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
            rewrite_prompt = f"""
Rewrite the message below to remove any mention of: scam, scammer, fraud, phishing, suspicious.
Keep it natural, cautious, and 1-2 short sentences. Do not accuse or warn. Ask for an official link or helpline to verify.

Message:
{reply}
""".strip()
            rewritten = call_llm_for_reply(rewrite_prompt).strip()
            if rewritten and not any(b in rewritten.lower() for b in banned):
                reply = rewritten
            elif strict:
                raise ValueError("Model produced disallowed wording in reply.")

        return {
            "reply": reply,
            "fallback": False,
            "reason": None,
        }

    except Exception:
        if strict:
            raise
        # Safe fallback that still fits the persona
        return {"reply": PASSIVE_FALLBACK_REPLY, "fallback": True, "reason": "LLM unavailable, fallback reply used"}
