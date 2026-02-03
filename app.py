from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import ScamCheckRequest, ScamCheckResponse
from models.honeypot_schemas import HoneypotRequest, HoneypotResponse, IntelligencePayload
from models.victim_agent_schemas import VictimReplyRequest, VictimReplyResponse
from models.hackathon_schemas import HackathonRequest, HackathonResponse

from detection.scam_classifier import classify_message
from reasoning.victim_agent import generate_passive_reply
from extraction.extractor import extract_intelligence
from agent.controller import decide_agent_mode
from reasoning.analyst import analyze_intelligence
from config.settings import settings
import requests

app = FastAPI(
    title="Agentic Honey-Pot – Scam Classification API",
    description=(
        "Stage-1 AI scam classification with confidence scoring. "
        "Stage-2 victim agent reply generation. "
        "Stage-3 optional intelligence analysis."
    ),
    version="1.2.0"
)

# --------------------------------------------------
# CORS middleware for flexibility in testing from web UIs
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# API key auth
# --------------------------------------------------
def require_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    # Some API tester UIs use lowercase headers; FastAPI normalizes, but keep strict alias.
    if not settings.API_KEY:
        raise HTTPException(status_code=500, detail="Server API key not configured")

    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return True

# --------------------------------------------------
# In-memory conversation memory
# --------------------------------------------------
conversation_memory = {}
callback_sent = set()


def _build_intel_payload(intel: dict) -> IntelligencePayload:
    return IntelligencePayload(
        bankAccounts=intel.get("bank_accounts", []),
        upiIds=intel.get("upi_ids", []),
        phishingLinks=intel.get("urls", []),
        phoneNumbers=intel.get("phone_numbers", []),
        suspiciousKeywords=intel.get("tactics", []),
    )


def _maybe_send_callback(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    intel_payload: IntelligencePayload,
    agent_notes: str,
):
    if not settings.CALLBACK_ENABLED:
        return
    if not scam_detected:
        return
    if total_messages < settings.CALLBACK_MIN_TURNS:
        return
    if session_id in callback_sent:
        return

    payload = {
        "sessionId": session_id,
        "scamDetected": scam_detected,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": {
            "bankAccounts": intel_payload.bankAccounts,
            "upiIds": intel_payload.upiIds,
            "phishingLinks": intel_payload.phishingLinks,
            "phoneNumbers": intel_payload.phoneNumbers,
            "suspiciousKeywords": intel_payload.suspiciousKeywords,
        },
        "agentNotes": agent_notes,
    }

    try:
        requests.post(settings.CALLBACK_URL, json=payload, timeout=5)
        callback_sent.add(session_id)
    except Exception:
        pass


# --------------------------------------------------
# Stage-2 only endpoint (optional)
# --------------------------------------------------
@app.post("/victim_reply", response_model=VictimReplyResponse, dependencies=[Depends(require_api_key)])
def victim_reply(request: VictimReplyRequest):
    result = generate_passive_reply(
        last_message=request.last_message,
        conversation_id=request.conversation_id,
        risk=request.risk,
        agent_mode=request.agent_mode,
        memory=None
    )
    return VictimReplyResponse(
        reply=result["reply"],
        fallback=result["fallback"],
        reason=result["reason"]
    )


# --------------------------------------------------
# Full pipeline endpoint
# --------------------------------------------------
@app.post("/detect", response_model=ScamCheckResponse, dependencies=[Depends(require_api_key)])
def detect_scam(request: ScamCheckRequest):

    cid = request.conversation_id
    text = request.text.strip()

    # Initialize memory if new conversation
    if cid not in conversation_memory:
        conversation_memory[cid] = []

    # Store scammer message (ALWAYS)
    conversation_memory[cid].append({
        "role": "scammer",
        "content": text
    })

    # --------------------------------------------------
    # Short-circuit trivial messages
    # --------------------------------------------------
    if len(text) < 6:
        reply_text = "Hello… could you tell me more about what this is regarding?"

        conversation_memory[cid].append({
            "role": "agent",
            "content": reply_text
        })

        return ScamCheckResponse(
            is_scam=False,
            confidence=0.0,
            reason="Message too short to classify",
            risk=0.0,
            agent_mode="confused",
            agent_reply=reply_text,
            intelligence={},
            analyst_summary=None
        )

    # --------------------------------------------------
    # Stage-1: Scam classification
    # --------------------------------------------------
    result = classify_message(text)

    # --------------------------------------------------
    # Intelligence extraction
    # --------------------------------------------------
    intel = extract_intelligence(text)

    # --------------------------------------------------
    # Agent controller
    # --------------------------------------------------
    risk_score = result["risk"]

    if risk_score > 0.7:
        risk_level = "high"
    elif risk_score > 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"

    agent_mode = decide_agent_mode(
        risk_level=risk_level,
        turns=len(conversation_memory[cid])
    )

    # --------------------------------------------------
    # Stage-2: Victim agent reply (WITH MEMORY)
    # --------------------------------------------------
    reply_result = generate_passive_reply(
        last_message=text,
        conversation_id=cid,
        risk=risk_score,
        agent_mode=agent_mode,
        memory=conversation_memory[cid]
    )

    # Store agent reply
    conversation_memory[cid].append({
        "role": "agent",
        "content": reply_result["reply"]
    })

    # --------------------------------------------------
    # Stage-3: Analyst summary (conditional)
    # --------------------------------------------------
    analyst_summary = None
    if (
        result["confidence"] > 0.85
        or intel.get("urls")
        or intel.get("upi_ids")
    ):
        analyst_summary = analyze_intelligence(intel)

    # --------------------------------------------------
    # Final response
    # --------------------------------------------------
    return ScamCheckResponse(
        is_scam=result["is_scam"],
        confidence=result["confidence"],
        reason=result.get("reason"),
        risk=risk_score,
        agent_mode=agent_mode,
        agent_reply=reply_result["reply"],
        intelligence=intel,
        analyst_summary=analyst_summary
    )


# --------------------------------------------------
# Hackathon Honeypot endpoint (required schema)
# --------------------------------------------------
@app.post("/honeypot", response_model=HoneypotResponse, dependencies=[Depends(require_api_key)])
def honeypot_endpoint(request: HoneypotRequest):
    session_id = request.sessionId
    incoming_text = request.message.text.strip()

    # Rebuild memory from provided history if available
    if request.conversationHistory:
        conversation_memory[session_id] = []
        for msg in request.conversationHistory:
            role = "scammer" if msg.sender == "scammer" else "agent"
            conversation_memory[session_id].append({
                "role": role,
                "content": msg.text
            })
    else:
        conversation_memory.setdefault(session_id, [])

    # Append latest message
    conversation_memory[session_id].append({
        "role": "scammer" if request.message.sender == "scammer" else "agent",
        "content": incoming_text
    })

    # Stage-1: Scam classification
    result = classify_message(incoming_text)

    # Intelligence extraction (use full context if provided)
    all_text = " ".join([m["content"] for m in conversation_memory[session_id]])
    intel = extract_intelligence(all_text)
    intel_payload = _build_intel_payload(intel)

    # Agent controller
    risk_score = result["risk"]
    if risk_score > 0.7:
        risk_level = "high"
    elif risk_score > 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"

    agent_mode = decide_agent_mode(
        risk_level=risk_level,
        turns=len(conversation_memory[session_id])
    )

    # Stage-2: Agent reply
    reply_result = generate_passive_reply(
        last_message=incoming_text,
        conversation_id=session_id,
        risk=risk_score,
        agent_mode=agent_mode,
        memory=conversation_memory[session_id]
    )

    conversation_memory[session_id].append({
        "role": "agent",
        "content": reply_result["reply"]
    })

    total_messages = len(conversation_memory[session_id])
    agent_notes = "Scam tactics detected: " + ", ".join(intel.get("tactics", [])) if intel.get("tactics") else "No strong scam tactics detected yet"

    # Optional analyst summary to improve notes
    if result["confidence"] > 0.85 or intel_payload.phishingLinks or intel_payload.upiIds:
        analyst_summary = analyze_intelligence(intel)
        if isinstance(analyst_summary, dict) and analyst_summary.get("recommended_strategy"):
            agent_notes = analyst_summary.get("recommended_strategy")

    _maybe_send_callback(
        session_id=session_id,
        scam_detected=result["is_scam"],
        total_messages=total_messages,
        intel_payload=intel_payload,
        agent_notes=agent_notes,
    )

    return HoneypotResponse(
        status="success",
        reply=reply_result["reply"]
    )
# --------------------------------------------------
# Hackathon schema endpoint
# --------------------------------------------------
@app.post("/hackathon/detect", response_model=HackathonResponse, dependencies=[Depends(require_api_key)])
def hackathon_detect(req: HackathonRequest):
    """
    Accepts the hackathon's input schema and returns a minimal reply object.
    Uses the same pipeline components under the hood.
    """
    session_id = req.sessionId
    latest_text = req.message.text.strip()

    # Map hackathon history into our memory format
    memory = []
    for m in req.conversationHistory[-6:]:
        memory.append({
            "role": "scammer" if m.sender == "scammer" else "agent",
            "content": m.text
        })

    # Classify and extract
    result = classify_message(latest_text)
    intel = extract_intelligence(latest_text)

    risk_score = result["risk"]
    risk_level = "high" if risk_score > 0.7 else ("medium" if risk_score > 0.4 else "low")
    agent_mode = decide_agent_mode(risk_level=risk_level, turns=len(memory))

    reply_result = generate_passive_reply(
        last_message=latest_text,
        conversation_id=session_id,
        risk=risk_score,
        agent_mode=agent_mode,
        memory=memory
    )

    return HackathonResponse(status="success", reply=reply_result["reply"]) 

# --------------------------------------------------
# Health Check Endpoint
# --------------------------------------------------
@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring and deployment.
    """
    return {"status": "healthy", "version": "1.2.0"}

# --------------------------------------------------
# Debug / Observability Endpoint
# --------------------------------------------------
@app.get("/memory/{conversation_id}", dependencies=[Depends(require_api_key)])
def get_conversation_memory(conversation_id: str):
    """
    Returns the stored conversation memory for debugging
    and inspection purposes.
    """
    return {
        "conversation_id": conversation_id,
        "turns": conversation_memory.get(conversation_id, [])
    }
