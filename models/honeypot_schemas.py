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


class IntelligencePayload(BaseModel):
    bankAccounts: List[str] = Field(default_factory=list)
    upiIds: List[str] = Field(default_factory=list)
    phishingLinks: List[str] = Field(default_factory=list)
    phoneNumbers: List[str] = Field(default_factory=list)
    suspiciousKeywords: List[str] = Field(default_factory=list)


class HoneypotRequest(BaseModel):
    sessionId: str = Field(...)
    message: MessageModel = Field(...)
    conversationHistory: List[MessageModel] = Field(default_factory=list)
    metadata: Optional[MetadataModel] = None


class HoneypotResponse(BaseModel):
    status: str = Field("success")
    reply: str
