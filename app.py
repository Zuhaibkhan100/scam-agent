from __future__ import annotations

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import json
import requests
import time
from typing import Dict, List, Any

from config.settings import settings
from models.hackathon_schemas import HackathonRequest, HackathonResponse
from reasoning.final_intelligence import generate_final_intelligence
from reasoning.victim_agent import generate_passive_reply
from extraction.extractor import extract_intelligence

# Server-side session storage to accumulate intelligence across all messages
_session_store: Dict[str, List[Dict[str, Any]]] = {}
_session_seen: Dict[str, set[tuple]] = {}

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
def require_api_key(
    x_api_key: str | None = Header(None, alias="x-api-key"),
    api_key: str | None = Header(None, alias="api-key"),
    apikey: str | None = Header(None, alias="apikey"),
    api_key_q: str | None = Query(None, alias="api_key"),
    authorization: str | None = Header(None, alias="authorization"),
) -> None:
    if not settings.API_KEY:
        raise HTTPException(status_code=500, detail="Server API key not configured")

    provided = x_api_key or api_key or apikey or api_key_q
    if not provided and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            provided = parts[1].strip()

    if provided != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# --------------------------------------------------
# Callback bookkeeping (best-effort, in-memory)
# --------------------------------------------------
_callback_sent: set[str] = set()


def _diag(event: str, data: dict) -> None:
    if not getattr(settings, "DIAGNOSTICS", False):
        return
    try:
        print(f"[DIAG] {event} {json.dumps(data, ensure_ascii=True, sort_keys=True)}")
    except Exception:
        # Last-resort: avoid crashing the request due to logging issues.
        print(f"[DIAG] {event} {data}")


def _message_key(sender: str | None, text: str | None, timestamp: int | None) -> tuple:
    return (
        (sender or "").strip().lower(),
        (text or "").strip(),
        int(timestamp) if timestamp is not None else None,
    )


def _append_message(
    session_id: str,
    *,
    sender: str | None,
    text: str | None,
    timestamp: int | None,
) -> None:
    key = _message_key(sender, text, timestamp)
    seen = _session_seen.setdefault(session_id, set())
    if key in seen:
        return
    seen.add(key)

    _session_store.setdefault(session_id, []).append(
        {
            "role": "scammer" if (sender or "").lower() == "scammer" else "agent",
            "text": text or "",
            "sender": sender or "user",
        }
    )


def _scammer_text_only(conversation_history: list) -> str:
    lines: list[str] = []
    for m in conversation_history:
        sender = getattr(m, "sender", None) or (m.get("sender") if isinstance(m, dict) else None)
        text = getattr(m, "text", None) or (m.get("text") if isinstance(m, dict) else "")
        if str(sender).lower() != "scammer":
            continue
        t = str(text or "").strip()
        if t:
            lines.append(t)
    return "\n".join(lines)


def _callback_gate_details(
    *,
    total_messages_exchanged: int,
    conversation_history: list,
) -> tuple[bool, dict[str, Any]]:
    if total_messages_exchanged < settings.CALLBACK_MIN_TURNS:
        return (
            False,
            {
                "reason": "below_min_turns",
                "total_messages_exchanged": total_messages_exchanged,
                "min_turns": settings.CALLBACK_MIN_TURNS,
            },
        )

    scammer_text = _scammer_text_only(conversation_history)
    hints = extract_intelligence(scammer_text)
    urls = hints.get("urls", [])
    upi_ids = hints.get("upi_ids", [])
    phone_numbers = hints.get("phone_numbers", [])
    bank_accounts = hints.get("bank_accounts", [])

    concrete_signals = len(urls) + len(upi_ids) + len(phone_numbers) + len(bank_accounts)
    category_count = sum(1 for group in (urls, upi_ids, phone_numbers, bank_accounts) if group)

    min_categories = int(getattr(settings, "CALLBACK_MIN_INDICATOR_CATEGORIES", 2))
    if min_categories < 1:
        min_categories = 1

    force_extra_turns = int(getattr(settings, "CALLBACK_FORCE_EXTRA_TURNS", 6))
    if force_extra_turns < 0:
        force_extra_turns = 0

    needed_turns = settings.CALLBACK_MIN_TURNS + force_extra_turns

    counts = {
        "urls": len(urls),
        "upi_ids": len(upi_ids),
        "phone_numbers": len(phone_numbers),
        "bank_accounts": len(bank_accounts),
    }

    # Primary gate: wait for enough *different* indicator categories.
    if category_count >= min_categories:
        return (
            True,
            {
                "reason": "enough_categories",
                "total_messages_exchanged": total_messages_exchanged,
                "min_turns": settings.CALLBACK_MIN_TURNS,
                "min_indicator_categories": min_categories,
                "force_extra_turns": force_extra_turns,
                "needed_turns": needed_turns,
                "category_count": category_count,
                "concrete_signals": concrete_signals,
                "counts": counts,
            },
        )

    # Fallback: force-send after enough extra turns, even if indicators are sparse.
    if total_messages_exchanged >= needed_turns:
        return (
            True,
            {
                "reason": "force_timeout_reached",
                "total_messages_exchanged": total_messages_exchanged,
                "min_turns": settings.CALLBACK_MIN_TURNS,
                "min_indicator_categories": min_categories,
                "force_extra_turns": force_extra_turns,
                "needed_turns": needed_turns,
                "category_count": category_count,
                "concrete_signals": concrete_signals,
                "counts": counts,
            },
        )

    return (
        False,
        {
            "reason": "waiting_for_more_categories",
            "total_messages_exchanged": total_messages_exchanged,
            "min_turns": settings.CALLBACK_MIN_TURNS,
            "min_indicator_categories": min_categories,
            "force_extra_turns": force_extra_turns,
            "needed_turns": needed_turns,
            "category_count": category_count,
            "concrete_signals": concrete_signals,
            "counts": counts,
        },
    )


def _maybe_send_callback(
    *,
    session_id: str,
    total_messages_exchanged: int,
    conversation_history: list,
    latest_sender: str,
    latest_text: str,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    """
    Mandatory hackathon callback.
    Sent once per session after scam is detected and engagement is considered sufficient.
    """
    if not settings.CALLBACK_ENABLED:
        _diag("callback_skip", {"sessionId": session_id, "reason": "callback_disabled"})
        return
    if session_id in _callback_sent:
        _diag("callback_skip", {"sessionId": session_id, "reason": "already_sent"})
        return

    # "Sufficient engagement" is enforced by a minimum message count.
    should_send, gate = _callback_gate_details(
        total_messages_exchanged=total_messages_exchanged,
        conversation_history=conversation_history,
    )
    _diag(
        "callback_gate",
        {
            "sessionId": session_id,
            "history_len": len(conversation_history or []),
            "store_len": len(_session_store.get(session_id, [])),
            **gate,
        },
    )
    if not should_send:
        return

    def _post_callback() -> None:
        try:
            payload = generate_final_intelligence(
                session_id=session_id,
                total_messages_exchanged=total_messages_exchanged,
                conversation_history=conversation_history,
                latest_sender=latest_sender,
                latest_text=latest_text,
            )
        except Exception as e:
            print(f"Callback generation error for session {session_id}: {e}")
            _diag("callback_error", {"sessionId": session_id, "stage": "generate_final_intelligence", "error": str(e)})
            return

        if not payload:
            print(f"Callback generation returned empty payload for session {session_id}")
            _diag("callback_error", {"sessionId": session_id, "stage": "empty_payload"})
            return

        if not payload.get("scamDetected", False):
            # Best-effort: only report once the model considers it a scam.
            _diag("callback_skip", {"sessionId": session_id, "reason": "scamDetected_false"})
            return

        _diag(
            "callback_payload",
            {
                "sessionId": session_id,
                "payload_totalMessagesExchanged": payload.get("totalMessagesExchanged"),
                "payload_extractedIntelligence": payload.get("extractedIntelligence", {}),
                "payload_agentNotes": str(payload.get("agentNotes", ""))[:200],
                "dry_run": bool(settings.CALLBACK_DRY_RUN),
            },
        )

        if settings.CALLBACK_DRY_RUN:
            _callback_sent.add(session_id)
            print(f"[DRY RUN] Callback payload for session {session_id}: {payload}")
            return

        for attempt in range(2):
            try:
                response = requests.post(settings.CALLBACK_URL, json=payload, timeout=5)
                if 200 <= response.status_code < 300:
                    _callback_sent.add(session_id)
                    print(f"Callback sent successfully for session {session_id}")
                    _diag(
                        "callback_sent",
                        {"sessionId": session_id, "status_code": response.status_code},
                    )
                    return

                # Best-effort: do not fail the API response.
                # Print only ASCII to avoid encoding surprises in logs.
                print(
                    f"Callback failed for session {session_id}: {response.status_code} - {response.text}"
                )
                _diag(
                    "callback_failed",
                    {
                        "sessionId": session_id,
                        "status_code": response.status_code,
                        "response_text": (response.text or "")[:300],
                    },
                )
            except Exception as e:
                print(f"Callback error for session {session_id}: {e}")
                _diag("callback_error", {"sessionId": session_id, "stage": "requests.post", "error": str(e)})

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
    history_len = len(req.conversationHistory or [])
    history_scammer = sum(1 for m in (req.conversationHistory or []) if m.sender == "scammer")
    history_user = history_len - history_scammer

    _diag(
        "request",
        {
            "sessionId": session_id,
            "latest_sender": latest_sender,
            "latest_text_prefix": latest_text[:120],
            "latest_timestamp": req.message.timestamp,
            "conversationHistory_len": history_len,
            "conversationHistory_counts": {"scammer": history_scammer, "user": history_user},
            "callback_already_sent": session_id in _callback_sent,
            "app_version": app.version,
        },
    )

    # Convert history into the memory format expected by the victim agent:
    # hackathon sender "user" corresponds to our honeypot agent.
    memory = [
        {"role": ("scammer" if m.sender == "scammer" else "agent"), "content": (m.text or "")}
        for m in req.conversationHistory
    ]

    # Only classify/engage as "scammer" when the platform says the latest message is from the scammer.
    if latest_sender != "scammer" or not latest_text:
        return HackathonResponse(status="success", reply="Could you share the exact message they sent you?")

    reply_result = generate_passive_reply(
        last_message=latest_text,
        conversation_id=session_id,
        risk=None,
        agent_mode="confused",
        memory=memory,
    )
    reply_text = (reply_result.get("reply") or "").strip() or "Sorry, can you explain that again?"

    # Accumulate messages server-side with de-duplication.
    for m in req.conversationHistory:
        _append_message(
            session_id,
            sender=m.sender,
            text=m.text,
            timestamp=m.timestamp,
        )

    _append_message(
        session_id,
        sender=latest_sender,
        text=latest_text,
        timestamp=req.message.timestamp,
    )

    accumulated_history = _session_store.get(session_id, [])
    total_messages_exchanged = len(accumulated_history) + 1  # +1 for our reply

    _diag(
        "session_state",
        {
            "sessionId": session_id,
            "accumulated_history_len": len(accumulated_history),
            "total_messages_exchanged": total_messages_exchanged,
        },
    )

    _maybe_send_callback(
        session_id=session_id,
        total_messages_exchanged=total_messages_exchanged,
        conversation_history=accumulated_history,
        latest_sender=latest_sender,
        latest_text=latest_text,
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
