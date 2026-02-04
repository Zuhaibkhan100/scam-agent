from __future__ import annotations

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import requests
import time

from config.settings import settings
from models.hackathon_schemas import HackathonRequest, HackathonResponse
from reasoning.final_intelligence import generate_final_intelligence
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
        return
    if session_id in _callback_sent:
        return

    # "Sufficient engagement" is enforced by a minimum message count.
    if total_messages_exchanged < settings.CALLBACK_MIN_TURNS:
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
            return

        if not payload:
            print(f"Callback generation returned empty payload for session {session_id}")
            return

        if not payload.get("scamDetected", False):
            # Best-effort: only report once the model considers it a scam.
            return

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

    # Total messages exchanged should count BOTH sides; this callback is sent after we generate our reply.
    total_messages_exchanged = len(req.conversationHistory) + 2

    _maybe_send_callback(
        session_id=session_id,
        total_messages_exchanged=total_messages_exchanged,
        conversation_history=req.conversationHistory,
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
