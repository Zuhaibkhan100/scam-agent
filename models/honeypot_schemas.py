from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal


class MessageModel(BaseModel):
    sender: Literal["scammer", "user"] = Field(...)
    text: str = Field(...)
    timestamp: Optional[int] = Field(None, description="Epoch time format in ms")

    @field_validator("sender", mode="before")
    @classmethod
    def _normalize_sender(cls, v: object) -> str:
        if v is None:
            raise ValueError("sender is required")
        s = str(v).strip().lower()
        if s == "scammer":
            return "scammer"
        return "user"

    @field_validator("text", mode="before")
    @classmethod
    def _normalize_text(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v)


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

    @field_validator("conversationHistory", mode="before")
    @classmethod
    def _normalize_history(cls, v: object) -> list:
        if v is None:
            return []
        return v


class HoneypotResponse(BaseModel):
    status: str = Field("success")
    reply: str
