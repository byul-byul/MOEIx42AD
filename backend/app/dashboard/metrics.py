# /backend/app/dashboard/metrics.py
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.core.redis import get_redis
from app.models import Message, MessageRole, Ticket, TicketStatus

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)) -> dict:
    redis = get_redis()
    session_keys = await redis.keys("session:*")
    active_sessions = len(session_keys)

    # Ticket counts by status
    ticket_counts: dict[str, int] = {}
    for status in TicketStatus:
        result = await db.execute(select(func.count()).where(Ticket.status == status))
        ticket_counts[status.value] = result.scalar() or 0

    total_result = await db.execute(select(func.count()).select_from(Ticket))
    total_tickets = total_result.scalar() or 0

    # Messages by channel
    channel_result = await db.execute(
        select(Message.channel, func.count(Message.id))
        .where(Message.role == MessageRole.user)
        .group_by(Message.channel)
    )
    messages_by_channel = {row[0].value: row[1] for row in channel_result}

    # Sentiment distribution (user messages only)
    sentiment_result = await db.execute(
        select(Message.sentiment, func.count(Message.id))
        .where(Message.role == MessageRole.user, Message.sentiment.isnot(None))
        .group_by(Message.sentiment)
    )
    sentiment_stats = {(row[0] or "neutral"): row[1] for row in sentiment_result}

    # Recent tickets (last 10)
    recent_result = await db.execute(
        select(Ticket).order_by(Ticket.created_at.desc()).limit(10)
    )
    recent_tickets = [
        {
            "id": t.id,
            "channel": t.channel.value,
            "status": t.status.value,
            "escalate": t.escalate,
            "created_at": t.created_at.isoformat(),
        }
        for t in recent_result.scalars()
    ]

    return {
        "active_sessions": active_sessions,
        "tickets": {"total": total_tickets, **ticket_counts},
        "messages_by_channel": messages_by_channel,
        "sentiment_stats": sentiment_stats,
        "recent_tickets": recent_tickets,
    }


@router.get("/copilot")
async def get_copilot(db: AsyncSession = Depends(get_db)) -> dict:
    """Return recent conversation turns for the human agent co-pilot panel."""
    # Fetch the last 20 user messages with their immediately following agent message
    user_msgs_result = await db.execute(
        select(Message)
        .where(Message.role == MessageRole.user)
        .order_by(Message.timestamp.desc())
        .limit(10)
    )
    user_msgs = user_msgs_result.scalars().all()

    suggestions = []
    for um in user_msgs:
        # Find the agent reply for the same session closest in time after user message
        agent_result = await db.execute(
            select(Message)
            .where(
                Message.session_id == um.session_id,
                Message.role == MessageRole.agent,
                Message.timestamp >= um.timestamp,
            )
            .order_by(Message.timestamp.asc())
            .limit(1)
        )
        agent_msg = agent_result.scalar_one_or_none()

        suggestions.append({
            "session_id": um.session_id,
            "channel": um.channel.value,
            "user_message": um.text,
            "suggested_reply": agent_msg.text if agent_msg else None,
            "sentiment": um.sentiment or "neutral",
            "timestamp": um.timestamp.isoformat(),
        })

    return {"suggestions": suggestions}
