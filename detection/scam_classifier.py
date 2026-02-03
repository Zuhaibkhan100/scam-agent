from reasoning.llm_client import call_llm


def classify_message(text: str) -> dict:
    """
    Stage-1 AI-only scam classification.

    Input:
        text (str): raw incoming message

    Output (dict):
        {
            "is_scam": bool,
            "confidence": float (0.0 - 1.0),
            "reason": str
        }
    """

    # -------------------------------
    # Prompt for probabilistic scam classification
    # -------------------------------
    prompt = f"""
You are a cybersecurity fraud analyst.

Your task is to assess whether the following message is a scam.

Definition:
A scam is any message intended to deceive a person for financial gain,
credential theft, impersonation of authority, or coercive manipulation.

Instructions:
- Analyze intent, not just wording
- Consider impersonation, urgency, manipulation, or requests for action
- Be conservative in uncertain cases

Output STRICTLY in JSON format:
{{
  "scam": true or false,
  "confidence": number between 0.0 and 1.0,
  "reason": "one-sentence justification"
}}

Message:
\"\"\"{text}\"\"\"
"""

    # -------------------------------
    # Call LLM (via llm_client)
    # -------------------------------
    llm_result = call_llm(prompt)

    # -------------------------------
    # Normalize and safeguard output
    # -------------------------------
    is_scam = bool(llm_result.get("scam", False))
    confidence = llm_result.get("confidence", 0.5)
    reason = llm_result.get("reason", "")

    # Clamp confidence to [0.0, 1.0]
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.5
    confidence = max(0.0, min(confidence, 1.0))

    # --- Risk score logic: if scam, risk = confidence; if not scam, risk = 0 ---
    # This means: risk is only high if we're confident it's actually a scam
    risk = confidence if is_scam else 0.0
    risk = max(0.0, min(risk, 1.0))

    # --- Agent mode suggestion: escalate if high risk, stall if medium, confused if low ---
    if risk > 0.7:
        agent_mode = "escalate"
    elif risk > 0.4:
        agent_mode = "stall"
    else:
        agent_mode = "confused"

    return {
        "is_scam": is_scam,
        "confidence": confidence,
        "reason": reason,
        "risk": risk,
        "agent_mode": agent_mode
    }
