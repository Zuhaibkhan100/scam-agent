"""
Decision Policy stub for multi-agent honeypot pipeline.
This module will decide the next agent mode based on risk and other factors.
"""

def choose_agent_mode(risk: float, context: dict = None) -> str:
    """
    Decide agent mode based on risk score and context.
    For now, escalate if risk > 0.7, else passive.
    """
    if risk > 0.7:
        return "escalate"
    return "passive"
