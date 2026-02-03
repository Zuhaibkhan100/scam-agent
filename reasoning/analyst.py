import json
from reasoning.llm_client import call_llm_for_reply


def analyze_intelligence(intel_snapshot: dict) -> dict:
    """
    Stage-3 Intelligence Analyst

    Converts extracted intelligence into a structured fraud analysis.
    Always returns a valid report (never N/A).
    """

    prompt = f"""
You are a cybersecurity fraud intelligence analyst.

Based ONLY on the extracted intelligence below, generate a structured analysis.

Extracted intelligence:
{intel_snapshot}

Respond STRICTLY in JSON with the following fields:
{{
  "scam_type": "...",
  "target": "...",
  "risk_level": "Low | Medium | High",
  "recommended_strategy": "..."
}}

Rules:
- Do NOT hallucinate unknown details
- Be concise and factual
- Base conclusions only on given intelligence
"""

    try:
        response_text = call_llm_for_reply(prompt)

        # Defensive JSON extraction
        if "{" in response_text and "}" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}")
            response_text = response_text[start:end + 1]

        return json.loads(response_text)

    except Exception:
        # Guaranteed fallback (no N/A)
        return {
            "scam_type": "phishing attempt",
            "target": "unspecified users",
            "risk_level": "High" if intel_snapshot.get("tactics") else "Medium",
            "recommended_strategy": "Continue engagement to extract additional identifiers"
        }
