from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class MessageModel(BaseModel):
    sender: Literal["scammer", "user"] = Field(...)
    text: str = Field(...)
    timestamp: int = Field(..., description="Epoch time format in ms")


class MetadataModel(BaseModel):
    channel: Optional[str] = None
    language: Optional[str] = None
    locale: Optional[str] = None


class HackathonRequest(BaseModel):
    sessionId: str = Field(...)
    message: MessageModel = Field(...)
    conversationHistory: List[MessageModel] = Field(default_factory=list)
    metadata: Optional[MetadataModel] = None


class HackathonResponse(BaseModel):
    status: str = Field("success")
    reply: str
