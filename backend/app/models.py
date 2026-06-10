# /backend/app/models.py
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChannelType(str, PyEnum):
    telegram = "telegram"
    whatsapp = "whatsapp"
    voice = "voice"
    webchat = "webchat"


class TicketStatus(str, PyEnum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    escalated = "escalated"


class MessageRole(str, PyEnum):
    user = "user"
    agent = "agent"


class Customer(Base):
    """Channel-agnostic customer identity, keyed by phone number.

    Links User rows across channels (telegram/whatsapp/voice/webchat) so the
    dashboard can show a single cross-channel briefing per real-world person.
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    users: Mapped[list["User"]] = relationship("User", back_populates="customer")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[ChannelType] = mapped_column(SAEnum(ChannelType), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)

    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="users")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="user")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    channel: Mapped[ChannelType] = mapped_column(SAEnum(ChannelType), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus), default=TicketStatus.open
    )
    escalate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="tickets")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="ticket")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # nullable — messages exist independently of tickets for general inquiries
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    # nullable — set via resolve_user(); lets the dashboard join messages -> users -> customers
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[ChannelType] = mapped_column(SAEnum(ChannelType), nullable=False)
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Voice channel only: coarse tone label from prosody analysis
    # (agitated | calm | flat), see agent/prosody.py
    voice_tone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ticket: Mapped["Ticket | None"] = relationship("Ticket", back_populates="messages")
