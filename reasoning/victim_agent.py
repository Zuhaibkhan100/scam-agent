from reasoning.llm_client import call_llm_for_reply

PASSIVE_FALLBACK_REPLY = (
    "Sorry, I’m having trouble understanding. Can you explain again?"
)


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
- Do NOT accuse
- Do NOT warn
- Do NOT provide sensitive information
"""

    try:
        reply = call_llm_for_reply(prompt)

        if not reply or not isinstance(reply, str) or not reply.strip():
            raise ValueError("Empty reply from LLM")

        return {
            "reply": reply.strip(),
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
