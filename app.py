from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import ScamCheckRequest, ScamCheckResponse
from models.victim_agent_schemas import VictimReplyRequest, VictimReplyResponse

from detection.scam_classifier import classify_message
from reasoning.victim_agent import generate_passive_reply
from extraction.extractor import extract_intelligence
from agent.controller import decide_agent_mode
from reasoning.analyst import analyze_intelligence
from config.settings import settings

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
