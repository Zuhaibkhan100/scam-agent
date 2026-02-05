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

    # Avoid duplicating the latest message if the caller already included it
    # in conversation_history (common when server-side history is accumulated).
    last_matches_latest = False
    if conversation_history:
        last = conversation_history[-1]
        last_sender = getattr(last, "sender", None) or (last.get("sender") if isinstance(last, dict) else "")
        last_text = getattr(last, "text", None) or (last.get("text") if isinstance(last, dict) else "")
        last_matches_latest = (
            str(last_sender or "").strip().lower() == str(latest_sender or "").strip().lower()
            and str(last_text or "").strip() == str(latest_text or "").strip()
        )

    if not last_matches_latest:
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
    # IMPORTANT: Combine both lists and deduplicate
    combined_bank_accounts = _dedupe_preserve_order(bank_accounts + _as_str_list(hint_payload.get("bankAccounts")))
    combined_upi_ids = _dedupe_preserve_order(upi_ids + _as_str_list(hint_payload.get("upiIds")))
    combined_phishing_links = _dedupe_preserve_order(phishing_links + _as_str_list(hint_payload.get("phishingLinks")))
    combined_phone_numbers = _dedupe_preserve_order(phone_numbers + _as_str_list(hint_payload.get("phoneNumbers")))
    combined_keywords = _dedupe_preserve_order(suspicious_keywords + _as_str_list(hint_payload.get("suspiciousKeywords")))

    # Soft validation to reduce hallucination: keep only items that appear in the transcript
    # or match the expected pattern class.
    scammer_only = "\n".join([line for line in transcript.splitlines() if line.lower().startswith("scammer:")]).lower()
    full_transcript_lower = transcript.lower()

    def appears_in_transcript(s: str) -> bool:
        """Check if string appears anywhere in the transcript (not just scammer lines)"""
        return s.lower() in full_transcript_lower

    url_pat = re.compile(r"https?://|www\.", flags=re.I)
    upi_pat = re.compile(r"\b[\w.\-]{2,}@[a-zA-Z]{2,}\b")
    phone_pat = re.compile(r"^\+?\d[\d\s().-]{7,}\d$")
    bank_pat = re.compile(r"^\d{9,18}$")

    # Keep items that match the expected pattern OR appear in transcript
    # Pattern matching is primary validation to avoid losing concrete data
    # Bank accounts must be concrete numeric identifiers; do not allow
    # free-form phrases like "SBI account" even if they appear in transcript.
    bank_accounts_clean = []
    for b in combined_bank_accounts:
        digits_only = re.sub(r"\D", "", b)
        if bank_pat.fullmatch(digits_only or ""):
            bank_accounts_clean.append(digits_only)
    
    upi_ids_clean = [u for u in combined_upi_ids if upi_pat.search(u) or appears_in_transcript(u)]
    phishing_links_clean = [u for u in combined_phishing_links if url_pat.search(u) or appears_in_transcript(u)]
    phone_numbers_clean = [p for p in combined_phone_numbers if phone_pat.fullmatch(p) or appears_in_transcript(p)]
    suspicious_keywords = combined_keywords

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
        bankAccounts=_dedupe_preserve_order(bank_accounts_clean),
        upiIds=_dedupe_preserve_order(upi_ids_clean),
        phishingLinks=_dedupe_preserve_order(phishing_links_clean),
        phoneNumbers=_dedupe_preserve_order(phone_numbers_clean),
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
    if getattr(settings, "DIAGNOSTICS", False):
        try:
            print(
                "[DIAG] final_intel_hints "
                + json.dumps(
                    {
                        "sessionId": session_id,
                        "transcript_lines": len([ln for ln in transcript.splitlines() if ln.strip()]),
                        "hint_counts": {
                            "bankAccounts": len(hint_payload.get("bankAccounts", [])),
                            "upiIds": len(hint_payload.get("upiIds", [])),
                            "phishingLinks": len(hint_payload.get("phishingLinks", [])),
                            "phoneNumbers": len(hint_payload.get("phoneNumbers", [])),
                            "suspiciousKeywords": len(hint_payload.get("suspiciousKeywords", [])),
                        },
                        "hint_samples": {
                            "bankAccounts": (hint_payload.get("bankAccounts") or [])[:2],
                            "upiIds": (hint_payload.get("upiIds") or [])[:2],
                            "phishingLinks": (hint_payload.get("phishingLinks") or [])[:2],
                            "phoneNumbers": (hint_payload.get("phoneNumbers") or [])[:2],
                            "suspiciousKeywords": (hint_payload.get("suspiciousKeywords") or [])[:4],
                        },
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
            )
        except Exception:
            pass

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
    if getattr(settings, "DIAGNOSTICS", False):
        try:
            print(
                "[DIAG] final_intel_output "
                + json.dumps(
                    {
                        "sessionId": session_id,
                        "scamDetected": scam_detected,
                        "totalMessagesExchanged": int(total_messages_exchanged),
                        "extractedIntelligence": extracted_intel.model_dump(),
                        "agentNotes_prefix": agent_notes[:200],
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
            )
        except Exception:
            pass

    return {
        "sessionId": session_id,
        "scamDetected": scam_detected,
        "totalMessagesExchanged": int(total_messages_exchanged),
        "extractedIntelligence": extracted_intel.model_dump(),
        "agentNotes": agent_notes,
    }
