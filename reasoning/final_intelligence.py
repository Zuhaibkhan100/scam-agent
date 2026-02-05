from __future__ import annotations

import json
import re
from typing import Any

from config.settings import settings
from extraction.extractor import extract_intelligence
from models.honeypot_schemas import IntelligencePayload
from reasoning.llm_client import call_llm_for_json


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            s = str(v).strip()
            if s:
                out.append(s)
        return out
    s = str(value).strip()
    return [s] if s else []


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _build_transcript(conversation_history: list, latest_sender: str, latest_text: str) -> str:
    lines: list[str] = []
    for m in conversation_history[-20:]:
        sender = getattr(m, "sender", None) or (m.get("sender") if isinstance(m, dict) else "user")
        text = getattr(m, "text", None) or (m.get("text") if isinstance(m, dict) else "")
        sender_label = "Scammer" if str(sender).lower() == "scammer" else "User"
        t = str(text or "").strip()
        if t:
            lines.append(f"{sender_label}: {t}")

    latest_label = "Scammer" if str(latest_sender).lower() == "scammer" else "User"
    lt = str(latest_text or "").strip()
    if lt:
        lines.append(f"{latest_label}: {lt}")

    return "\n".join(lines).strip()


def _sanitize_intel(payload: dict[str, Any], transcript: str, hint_payload: dict) -> IntelligencePayload:
    intel = payload.get("extractedIntelligence") if isinstance(payload, dict) else None
    if not isinstance(intel, dict):
        intel = {}

    bank_accounts = _as_str_list(intel.get("bankAccounts"))
    upi_ids = _as_str_list(intel.get("upiIds"))
    phishing_links = _as_str_list(intel.get("phishingLinks"))
    phone_numbers = _as_str_list(intel.get("phoneNumbers"))
    suspicious_keywords = _as_str_list(intel.get("suspiciousKeywords"))

    # Merge with hint_payload (regex-extracted items) to ensure no data is lost
    bank_accounts = _dedupe_preserve_order(bank_accounts + _as_str_list(hint_payload.get("bankAccounts")))
    upi_ids = _dedupe_preserve_order(upi_ids + _as_str_list(hint_payload.get("upiIds")))
    phishing_links = _dedupe_preserve_order(phishing_links + _as_str_list(hint_payload.get("phishingLinks")))
    phone_numbers = _dedupe_preserve_order(phone_numbers + _as_str_list(hint_payload.get("phoneNumbers")))
    suspicious_keywords = _dedupe_preserve_order(suspicious_keywords + _as_str_list(hint_payload.get("suspiciousKeywords")))

    # Soft validation to reduce hallucination: keep only items that appear in the transcript
    # or match the expected pattern class.
    scammer_only = "\n".join([line for line in transcript.splitlines() if line.lower().startswith("scammer:")]).lower()

    def appears(s: str) -> bool:
        return s.lower() in scammer_only

    url_pat = re.compile(r"https?://", flags=re.I)
    upi_pat = re.compile(r"\b[\w.\-]{2,}@[a-zA-Z]{2,}\b")
    phone_pat = re.compile(r"^\+?\d[\d\s().-]{7,}\d$")
    bank_pat = re.compile(r"^\d{9,18}$")

    bank_accounts = [b for b in bank_accounts if appears(b) or bank_pat.fullmatch(re.sub(r"\D", "", b) or "")]
    upi_ids = [u for u in upi_ids if appears(u) or upi_pat.search(u)]
    phishing_links = [u for u in phishing_links if appears(u) or url_pat.search(u)]
    phone_numbers = [p for p in phone_numbers if appears(p) or phone_pat.fullmatch(p)]

    # Keywords are free-form; keep short phrases and try to keep only phrases
    # that appear in scammer messages to reduce hallucination.
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

    scammer_norm = _norm(scammer_only)
    filtered_keywords: list[str] = []
    for k in suspicious_keywords:
        kn = _norm(k)
        if not (1 <= len(k) <= 40):
            continue
        if kn and kn in scammer_norm:
            filtered_keywords.append(k)
    suspicious_keywords = filtered_keywords

    return IntelligencePayload(
        bankAccounts=_dedupe_preserve_order(bank_accounts),
        upiIds=_dedupe_preserve_order(upi_ids),
        phishingLinks=_dedupe_preserve_order(phishing_links),
        phoneNumbers=_dedupe_preserve_order(phone_numbers),
        suspiciousKeywords=_dedupe_preserve_order(suspicious_keywords),
    )


def generate_final_intelligence(
    *,
    session_id: str,
    total_messages_exchanged: int,
    conversation_history: list,
    latest_sender: str,
    latest_text: str,
) -> dict[str, Any] | None:
    """
    Returns an AI-generated intelligence object for the mandatory callback:
    {
      "scamDetected": bool,
      "extractedIntelligence": { ... },
      "agentNotes": str
    }
    """
    transcript = _build_transcript(conversation_history, latest_sender, latest_text)

    # Provide lightweight deterministic hints to improve accuracy, but the final output
    # is still generated by the model (and then sanitized for type/pattern safety).
    hints = extract_intelligence(transcript)
    hint_payload = {
        "bankAccounts": hints.get("bank_accounts", []),
        "upiIds": hints.get("upi_ids", []),
        "phishingLinks": hints.get("urls", []),
        "phoneNumbers": hints.get("phone_numbers", []),
        "suspiciousKeywords": hints.get("suspicious_keywords", []),
        "impersonation": hints.get("impersonation"),
        "tactics": hints.get("tactics", []),
    }

    prompt = f"""
You are an information extraction system for scam conversations.

Task:
From the transcript below, decide if this looks like a scam attempt and extract concrete indicators.
IMPORTANT: Only extract concrete indicators that appear in lines labeled "Scammer:" (ignore "User:" lines for extraction).

Return ONLY valid JSON (no markdown, no extra text) with this exact shape:
{{
  "scamDetected": true/false,
  "extractedIntelligence": {{
    "bankAccounts": [string],
    "upiIds": [string],
    "phishingLinks": [string],
    "phoneNumbers": [string],
    "suspiciousKeywords": [string]
  }},
  "agentNotes": "one short sentence about tactics/impersonation"
}}

Rules:
- Do not hallucinate. Only include items that are present in the transcript.
- Lists can be empty.
- Prefer unique values (no duplicates).
- suspiciousKeywords should be short phrases that appear in the Scammer lines (e.g. "urgent", "verify immediately", "account blocked").
    - agentNotes must be ONE natural sentence (no labels like "Impersonation:"/"Tactics:", no bullet points).
    - agentNotes must NOT accuse; just describe observed tactics (urgency, impersonation, OTP request, links, etc.).

Transcript:
{transcript if transcript else "(empty)"}

Hints (may be incomplete):
{json.dumps(hint_payload, ensure_ascii=False)}
""".strip()

    result = call_llm_for_json(prompt, retries=1)
    if not isinstance(result, dict):
        if settings.LLM_STRICT:
            raise RuntimeError("Gemini did not return a valid JSON object for intelligence extraction.")

        # Non-strict fallback: deterministic extraction (keeps hackathon callback working).
        extracted_intel = IntelligencePayload(
            bankAccounts=_dedupe_preserve_order(_as_str_list(hint_payload.get("bankAccounts"))),
            upiIds=_dedupe_preserve_order(_as_str_list(hint_payload.get("upiIds"))),
            phishingLinks=_dedupe_preserve_order(_as_str_list(hint_payload.get("phishingLinks"))),
            phoneNumbers=_dedupe_preserve_order(_as_str_list(hint_payload.get("phoneNumbers"))),
            suspiciousKeywords=_dedupe_preserve_order(_as_str_list(hint_payload.get("suspiciousKeywords"))),
        )
        scam_detected = bool(hints.get("tactics") or hints.get("suspicious_keywords") or hints.get("urls") or hints.get("upi_ids"))

        impersonation = hints.get("impersonation")
        tactics = hints.get("tactics", [])
        parts: list[str] = []
        if impersonation:
            parts.append(f"Impersonation: {impersonation}")
        if tactics:
            parts.append("Tactics: " + ", ".join([str(t) for t in tactics if str(t).strip()]))
        agent_notes = "; ".join(parts) if parts else "Engaged safely to extract indicators without sharing any sensitive information."

        return {
            "sessionId": session_id,
            "scamDetected": scam_detected,
            "totalMessagesExchanged": int(total_messages_exchanged),
            "extractedIntelligence": extracted_intel.model_dump(),
            "agentNotes": agent_notes,
        }

    scam_detected = bool(result.get("scamDetected", False))
    agent_notes = str(result.get("agentNotes", "") or "").strip()
    if not agent_notes:
        agent_notes = "Observed impersonation and pressure tactics while avoiding sharing any sensitive information."

    extracted_intel = _sanitize_intel(result, transcript, hint_payload)

    return {
        "sessionId": session_id,
        "scamDetected": scam_detected,
        "totalMessagesExchanged": int(total_messages_exchanged),
        "extractedIntelligence": extracted_intel.model_dump(),
        "agentNotes": agent_notes,
    }
