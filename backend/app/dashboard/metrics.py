# /backend/app/dashboard/metrics.py
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.core.redis import get_redis
from app.models import Message, Ticket, TicketStatus

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)) -> dict:
    # Active sessions from Redis
    redis = get_redis()
    session_keys = await redis.keys("session:*")
    active_sessions = len(session_keys)

    # Ticket counts by status
    ticket_counts: dict[str, int] = {}
    for status in TicketStatus:
        result = await db.execute(
            select(func.count()).where(Ticket.status == status)
        )
        ticket_counts[status.value] = result.scalar() or 0

    # Total tickets
    total_result = await db.execute(select(func.count()).select_from(Ticket))
    total_tickets = total_result.scalar() or 0

    # Messages by channel
    from sqlalchemy import text as sa_text
    channel_result = await db.execute(
        select(Ticket.channel, func.count(Message.id))
        .join(Message, Message.ticket_id == Ticket.id, isouter=True)
        .group_by(Ticket.channel)
    )
    messages_by_channel = {row[0].value: row[1] for row in channel_result}

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
        "tickets": {
            "total": total_tickets,
            **ticket_counts,
        },
        "messages_by_channel": messages_by_channel,
        "recent_tickets": recent_tickets,
    }
