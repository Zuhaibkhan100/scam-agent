def decide_agent_mode(risk_level: str, turns: int) -> str:
    """
    Decide how the victim agent should behave.
    """
    if risk_level == "high":
        return "escalate"
    if risk_level == "medium":
        if turns < 2:
            return "confused"
        return "stall"
    return "confused"
