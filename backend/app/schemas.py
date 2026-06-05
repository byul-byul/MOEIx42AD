# /backend/app/schemas.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    """Produced by every channel adapter and sent to the backend agent."""

    session_id: str = Field(..., examples=["telegram_12345"])
    channel: Literal["telegram", "whatsapp", "voice", "webchat"]
    user_id: str
    text: str
    language: Literal["en", "ar"] = "en"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentResponse(BaseModel):
    """Returned by the backend agent to every channel adapter."""

    session_id: str
    text: str
    intent: str = "general_inquiry"
    sentiment: str = "neutral"
    ticket_id: int | None = None
    escalate: bool = False


class HealthResponse(BaseModel):
    backend: str
    redis: str
    db: str
