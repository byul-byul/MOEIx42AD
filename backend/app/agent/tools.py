# /backend/app/agent/tools.py
from contextvars import ContextVar

from langchain_core.tools import tool
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.core.logger import get_logger
from app.models import ChannelType, Ticket, TicketStatus, User

logger = get_logger(__name__)

# Injected before each agent.ainvoke() call — propagates into tool coroutines
session_ctx: ContextVar[str] = ContextVar("session_id", default="")
channel_ctx: ContextVar[str] = ContextVar("channel", default="webchat")


@tool
async def create_ticket(issue_summary: str) -> str:
    """
    Create a support ticket for the customer when they report a problem,
    complaint, or service request that needs tracking. Returns the ticket ID.
    """
    session_id = session_ctx.get()
    channel_str = channel_ctx.get()

    parts = session_id.split("_", 1)
    channel_user_id = parts[1] if len(parts) == 2 else session_id

    try:
        channel = ChannelType(channel_str)
    except ValueError:
        channel = ChannelType.webchat

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(User).where(
                User.channel_user_id == channel_user_id,
                User.channel == channel,
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(channel_user_id=channel_user_id, channel=channel)
            db.add(user)
            await db.flush()

        ticket = Ticket(user_id=user.id, channel=channel, status=TicketStatus.open)
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)

    logger.info("Ticket #%d created | session=%s", ticket.id, session_id)
    return f"Ticket #{ticket.id} created. Our team will follow up shortly."


@tool
async def get_ticket_status(ticket_id: int) -> str:
    """Look up the current status of an existing support ticket by its numeric ID."""
    async with AsyncSessionFactory() as db:
        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = result.scalar_one_or_none()

    if not ticket:
        return f"No ticket found with ID #{ticket_id}."

    return (
        f"Ticket #{ticket.id} — "
        f"status: {ticket.status.value}, "
        f"channel: {ticket.channel.value}."
    )
