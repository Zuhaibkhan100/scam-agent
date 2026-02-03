from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import ScamCheckRequest, ScamCheckResponse
from models.hackathon_schemas import HackathonRequest, HackathonResponse
from models.victim_agent_schemas import VictimReplyRequest, VictimReplyResponse

from detection.scam_classifier import classify_message
from reasoning.victim_agent import generate_passive_reply
from extraction.extractor import extract_intelligence
from agent.controller import decide_agent_mode
from reasoning.analyst import analyze_intelligence
from agent.callback_handler import send_final_callback, should_finalize_engagement
from config.settings import settings

app = FastAPI(
    title="Agentic Honey-Pot – Scam Classification API",
    description=(
        "Stage-1 AI scam classification with confidence scoring. "
        "Stage-2 victim agent reply generation. "
        "Stage-3 optional intelligence analysis. "
        "GUVI-compliant honeypot with mandatory callback."
    ),
    version="1.3.0"
)

# --------------------------------------------------
# CORS middleware for flexibility in testing
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# API key authentication
# --------------------------------------------------
def require_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    if not settings.API_KEY:
        raise HTTPException(status_code=500, detail="Server API key not configured")
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

# --------------------------------------------------
# In-memory conversation memory (for /detect only)
# --------------------------------------------------
conversation_memory = {}
callback_sent = set()


# --------------------------------------------------
# Original /detect endpoint (backward compatible)
# --------------------------------------------------
@app.post("/detect", response_model=ScamCheckResponse, dependencies=[Depends(require_api_key)])
def detect_scam(request: ScamCheckRequest):
    """
    Original endpoint for backward compatibility.
    Uses internal memory management.
    """
    cid = request.conversation_id
    text = request.text.strip()

    if cid not in conversation_memory:
        conversation_memory[cid] = []

    conversation_memory[cid].append({
        "role": "scammer",
        "content": text
    })

    # Short-circuit trivial messages
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

    # Stage-1: Scam classification
    result = classify_message(text)

    # Intelligence extraction
    intel = extract_intelligence(text)

    # Agent controller
    risk_score = result["risk"]
    risk_level = "high" if risk_score > 0.7 else ("medium" if risk_score > 0.4 else "low")
    agent_mode = decide_agent_mode(risk_level=risk_level, turns=len(conversation_memory[cid]))

    # Stage-2: Victim agent reply
    reply_result = generate_passive_reply(
        last_message=text,
        conversation_id=cid,
        risk=risk_score,
        agent_mode=agent_mode,
        memory=conversation_memory[cid]
    )

    conversation_memory[cid].append({
        "role": "agent",
        "content": reply_result["reply"]
    })

    # Stage-3: Analyst summary (conditional)
    analyst_summary = None
    if (
        result["confidence"] > 0.85
        or intel.get("urls")
        or intel.get("upi_ids")
    ):
        analyst_summary = analyze_intelligence(intel)

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
# GUVI Honeypot Endpoint (MAIN SUBMISSION ENDPOINT)
# --------------------------------------------------
@app.post("/honeypot/message", response_model=HackathonResponse, dependencies=[Depends(require_api_key)])
def honeypot_message(req: HackathonRequest):
    """
    GUVI-compliant honeypot endpoint.
    
    Architecture:
    - GUVI controls conversation lifecycle and sends conversationHistory
    - This endpoint is stateless (no internal memory)
    - Returns minimal response: {status, reply}
    - Internally extracts intelligence and sends mandatory callback when ready
    
    Flow:
    1. Parse GUVI request (sessionId, message, conversationHistory, metadata)
    2. Classify scam intent
    3. Generate agent reply
    4. Extract intelligence from full conversation
    5. Decide if engagement is sufficient for final callback
    6. Send callback if conditions met
    7. Return minimal response
    """
    session_id = req.sessionId
    latest_text = req.message.text.strip()

    # Build memory from GUVI's conversationHistory (source of truth)
    memory = []
    for m in req.conversationHistory:
        memory.append({
            "role": "scammer" if m.sender == "scammer" else "agent",
            "content": m.text
        })

    # Add latest message to memory
    memory.append({
        "role": "scammer" if req.message.sender == "scammer" else "agent",
        "content": latest_text
    })

    # Stage-1: Scam classification
    result = classify_message(latest_text)
    is_scam = result["is_scam"]
    confidence = result["confidence"]
    risk_score = result["risk"]

    # Intelligence extraction (from full conversation context)
    all_text = " ".join([m["content"] for m in memory])
    intel = extract_intelligence(all_text)

    # Count intelligence signals
    intel_signals = (
        len(intel.get("urls", [])) +
        len(intel.get("upi_ids", [])) +
        len(intel.get("phone_numbers", [])) +
        len(intel.get("emails", [])) +
        len(intel.get("bank_accounts", []))
    )

    # Agent controller
    risk_level = "high" if risk_score > 0.7 else ("medium" if risk_score > 0.4 else "low")
    agent_mode = decide_agent_mode(risk_level=risk_level, turns=len(memory))

    # Stage-2: Victim agent reply
    reply_result = generate_passive_reply(
        last_message=latest_text,
        conversation_id=session_id,
        risk=risk_score,
        agent_mode=agent_mode,
        memory=memory
    )

    # Decide if engagement is sufficient for final callback
    total_messages = len(memory) + 1  # include our reply
    should_callback = (
        is_scam and
        should_finalize_engagement(
            total_messages=total_messages,
            confidence=confidence,
            intel_signals=intel_signals
        )
    )

    # Send final callback if conditions met
    if should_callback and session_id not in callback_sent:
        intel_payload = {
            "bankAccounts": intel.get("bank_accounts", []),
            "upiIds": intel.get("upi_ids", []),
            "phishingLinks": intel.get("urls", []),
            "phoneNumbers": intel.get("phone_numbers", []),
            "suspiciousKeywords": intel.get("tactics", []),
        }
        agent_notes = f"Scam tactics: {', '.join(intel.get('tactics', []))}. Engagement depth: {total_messages} turns."
        sent = send_final_callback(
            session_id=session_id,
            scam_detected=is_scam,
            total_messages=total_messages,
            extracted_intelligence=intel_payload,
            agent_notes=agent_notes
        )
        if sent:
            callback_sent.add(session_id)

    # Return minimal response (GUVI expects only status and reply)
    return HackathonResponse(status="success", reply=reply_result["reply"])


# --------------------------------------------------
# Health Check Endpoint
# --------------------------------------------------
@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring and deployment.
    """
    return {"status": "healthy", "version": "1.3.0"}


# --------------------------------------------------
# Debug / Observability Endpoint
# --------------------------------------------------
@app.get("/memory/{conversation_id}", dependencies=[Depends(require_api_key)])
def get_conversation_memory(conversation_id: str):
    """
    Returns the stored conversation memory for debugging.
    Only works for /detect endpoint (internal memory).
    """
    return {
        "conversation_id": conversation_id,
        "turns": conversation_memory.get(conversation_id, [])
    }
