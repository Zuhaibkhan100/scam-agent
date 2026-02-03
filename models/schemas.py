from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ScamCheckRequest(BaseModel):
    """
    Input contract for stage-1 scam classification.
    Judges / clients will POST this JSON to the API.
    """
    conversation_id: str = Field(..., description="Unique conversation identifier (string)")
    text: str = Field(..., description="The raw incoming message text to classify")
    channel: Optional[str] = Field(None, description="Optional channel name (e.g. 'whatsapp', 'email')")


class ScamCheckResponse(BaseModel):
    """
    Enhanced full-pipeline response with all stages.
    """
    is_scam: bool = Field(..., description="Whether this message is judged as scam (True/False)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: Optional[str] = Field(None, description="One-sentence justification for the decision")
    risk: float = Field(..., ge=0.0, le=1.0, description="Risk score for the message (0.0-1.0)")
    agent_mode: Optional[str] = Field(None, description="Agent behavior mode (confused, stall, escalate)")
    agent_reply: Optional[str] = Field(None, description="Victim agent's generated reply")
    intelligence: Optional[Dict[str, Any]] = Field(None, description="Extracted intelligence (URLs, UPI, tactics)")
    analyst_summary: Optional[Dict[str, Any]] = Field(None, description="Stage-3 analyst summary (optional)")
