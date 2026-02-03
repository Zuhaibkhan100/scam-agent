from pydantic import BaseModel, Field
from typing import Optional

class VictimReplyRequest(BaseModel):
    """
    Input contract for Stage-2 victim agent reply generation.
    """
    conversation_id: str = Field(..., description="Unique conversation identifier")
    last_message: str = Field(..., description="The last scammer message to reply to")
    risk: Optional[float] = Field(None, description="Risk score from Stage-1")
    agent_mode: Optional[str] = Field(None, description="Agent mode suggestion from policy")

class VictimReplyResponse(BaseModel):
    """
    Output contract for Stage-2 victim agent reply.
    """
    reply: str = Field(..., description="Agent's generated reply to the scammer")
    fallback: bool = Field(False, description="True if a static fallback reply was used due to LLM failure")
    reason: Optional[str] = Field(None, description="Explanation or fallback reason if any")
