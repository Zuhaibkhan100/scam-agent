from __future__ import annotations

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import requests
import time

from agent.controller import decide_agent_mode
from config.settings import settings
from detection.scam_classifier import classify_message
from extraction.extractor import extract_intelligence
from models.hackathon_schemas import HackathonRequest, HackathonResponse
from models.honeypot_schemas import IntelligencePayload
from reasoning.victim_agent import generate_passive_reply

app = FastAPI(
    title="Agentic Honey-Pot - Scam Detection & Intelligence Extraction API",
    description=(
        "A GUVI hackathon-compatible honeypot API. "
        "Accepts message events, detects scam intent, engages autonomously, "
        "extracts intelligence, and sends the mandatory final callback."
    ),
    version="2.0.0",
)

# --------------------------------------------------
# CORS (optional; helpful for test UIs)
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# API key auth (require: x-api-key header)
# --------------------------------------------------
def require_api_key(x_api_key: str | None = Header(None, alias="x-api-key")) -> None:
    if not settings.API_KEY:
        raise HTTPException(status_code=500, detail="Server API key not configured")

    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# --------------------------------------------------
# Callback bookkeeping (best-effort, in-memory)
# --------------------------------------------------
_callback_sent: set[str] = set()


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _build_intel_payload(intel: dict) -> IntelligencePayload:
    return IntelligencePayload(
        bankAccounts=_dedupe_preserve_order([str(x) for x in intel.get("bank_accounts", []) if str(x).strip()]),
        upiIds=_dedupe_preserve_order([str(x) for x in intel.get("upi_ids", []) if str(x).strip()]),
        phishingLinks=_dedupe_preserve_order([str(x) for x in intel.get("urls", []) if str(x).strip()]),
        phoneNumbers=_dedupe_preserve_order([str(x) for x in intel.get("phone_numbers", []) if str(x).strip()]),
        suspiciousKeywords=_dedupe_preserve_order(
            [str(x) for x in intel.get("suspicious_keywords", []) if str(x).strip()]
        ),
    )


def _build_agent_notes(intel: dict) -> str:
    tactics = [str(x) for x in intel.get("tactics", []) if str(x).strip()]
    impersonation = intel.get("impersonation")

    parts: list[str] = []
    if impersonation:
        parts.append(f"Impersonation: {impersonation}")
    if tactics:
        parts.append("Tactics: " + ", ".join(tactics))

    if not parts:
        return "Engaged safely to extract scam indicators without sharing any sensitive information."
    return "; ".join(parts)


def _maybe_send_callback(
    *,
    session_id: str,
    scam_detected: bool,
    total_messages_exchanged: int,
    intel_payload: IntelligencePayload,
    agent_notes: str,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    """
    Mandatory hackathon callback.
    Sent once per session after scam is detected and engagement is considered sufficient.
    """
    if not settings.CALLBACK_ENABLED:
        return
    if not scam_detected:
        return
    if session_id in _callback_sent:
        return

    # "Sufficient engagement" is enforced by a minimum message count.
    if total_messages_exchanged < settings.CALLBACK_MIN_TURNS:
        return

    # Only send once we have extracted something useful (even keywords/tactics count).
    if not (
        intel_payload.bankAccounts
        or intel_payload.upiIds
        or intel_payload.phishingLinks
        or intel_payload.phoneNumbers
        or intel_payload.suspiciousKeywords
    ):
        return

    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": int(total_messages_exchanged),
        "extractedIntelligence": {
            "bankAccounts": intel_payload.bankAccounts,
            "upiIds": intel_payload.upiIds,
            "phishingLinks": intel_payload.phishingLinks,
            "phoneNumbers": intel_payload.phoneNumbers,
            "suspiciousKeywords": intel_payload.suspiciousKeywords,
        },
        "agentNotes": agent_notes,
    }

    def _post_callback() -> None:
        for attempt in range(2):
            try:
                response = requests.post(settings.CALLBACK_URL, json=payload, timeout=5)
                if 200 <= response.status_code < 300:
                    _callback_sent.add(session_id)
                    print(f"Callback sent successfully for session {session_id}")
                    return

                # Best-effort: do not fail the API response.
                # Print only ASCII to avoid encoding surprises in logs.
                print(
                    f"Callback failed for session {session_id}: {response.status_code} - {response.text}"
                )
            except Exception as e:
                print(f"Callback error for session {session_id}: {e}")

            # Small backoff before retrying.
            time.sleep(0.5 * (attempt + 1))

    if background_tasks is not None:
        background_tasks.add_task(_post_callback)
        return
    _post_callback()


def _handle_message_event(req: HackathonRequest, background_tasks: BackgroundTasks | None = None) -> HackathonResponse:
    """
    Implements the required hackathon flow:
    - Accept message + history
    - Detect scam intent
    - Engage autonomously with a human-like persona
    - Extract intelligence
    - Send mandatory final callback (once, best-effort)
    - Return minimal response: {status, reply}
    """
    session_id = req.sessionId
    latest_sender = req.message.sender
    latest_text = (req.message.text or "").strip()

    # Convert history into the memory format expected by the victim agent:
    # hackathon sender "user" corresponds to our honeypot agent.
    memory = [
        {"role": ("scammer" if m.sender == "scammer" else "agent"), "content": (m.text or "")}
        for m in req.conversationHistory
    ]

    # Always extract intelligence from full context (history + latest message).
    all_text = " ".join(
        [(m.text or "") for m in req.conversationHistory if m.sender == "scammer"] + [latest_text]
    ).strip()
    intel = extract_intelligence(all_text)
    intel_payload = _build_intel_payload(intel)
    agent_notes = _build_agent_notes(intel)

    # Only classify/engage as "scammer" when the platform says the latest message is from the scammer.
    if latest_sender != "scammer" or not latest_text:
        return HackathonResponse(status="success", reply="Could you share the exact message they sent you?")

    scammer_context = " ".join(
        [(m.text or "") for m in req.conversationHistory if m.sender == "scammer"][-4:] + [latest_text]
    ).strip()
    classification = classify_message(scammer_context)
    scam_detected = bool(classification.get("is_scam", False))
    risk_score = float(classification.get("risk", 0.0))

    risk_level = "high" if risk_score > 0.7 else ("medium" if risk_score > 0.4 else "low")
    agent_mode = decide_agent_mode(risk_level=risk_level, turns=len(req.conversationHistory))

    reply_result = generate_passive_reply(
        last_message=latest_text,
        conversation_id=session_id,
        risk=risk_score,
        agent_mode=agent_mode,
        memory=memory,
    )
    reply_text = (reply_result.get("reply") or "").strip() or "Sorry, can you explain that again?"

    # Total messages exchanged should count BOTH sides; this callback is sent after we generate our reply.
    total_messages_exchanged = len(req.conversationHistory) + 2

    _maybe_send_callback(
        session_id=session_id,
        scam_detected=scam_detected,
        total_messages_exchanged=total_messages_exchanged,
        intel_payload=intel_payload,
        agent_notes=agent_notes,
        background_tasks=background_tasks,
    )

    return HackathonResponse(status="success", reply=reply_text)


# --------------------------------------------------
# Hackathon Entry Points (all return EXACT {status, reply})
# --------------------------------------------------
@app.post("/", response_model=HackathonResponse, dependencies=[Depends(require_api_key)])
def root(req: HackathonRequest, background_tasks: BackgroundTasks) -> HackathonResponse:
    return _handle_message_event(req, background_tasks)


@app.get("/")
def root_get() -> dict:
    # Render/uptime checks often use GET/HEAD /. Keep this separate from POST /.
    return {"status": "ok", "service": "agentic-honeypot", "version": app.version}


@app.post("/detect", response_model=HackathonResponse, dependencies=[Depends(require_api_key)])
def detect(req: HackathonRequest, background_tasks: BackgroundTasks) -> HackathonResponse:
    return _handle_message_event(req, background_tasks)


@app.post("/honeypot", response_model=HackathonResponse, dependencies=[Depends(require_api_key)])
def honeypot(req: HackathonRequest, background_tasks: BackgroundTasks) -> HackathonResponse:
    return _handle_message_event(req, background_tasks)


@app.post("/honeypot/message", response_model=HackathonResponse, dependencies=[Depends(require_api_key)])
def honeypot_message(req: HackathonRequest, background_tasks: BackgroundTasks) -> HackathonResponse:
    return _handle_message_event(req, background_tasks)


@app.post("/hackathon/detect", response_model=HackathonResponse, dependencies=[Depends(require_api_key)])
def hackathon_detect(req: HackathonRequest, background_tasks: BackgroundTasks) -> HackathonResponse:
    return _handle_message_event(req, background_tasks)


# --------------------------------------------------
# Health Check (optional)
# --------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "version": app.version}
