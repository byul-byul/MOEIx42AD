# /backend/app/api/message.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.core import run_agent
from app.core.database import get_db
from app.core.logger import get_logger
from app.core.redis import get_session
from app.models import Message
from app.schemas import AgentResponse, IncomingMessage

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])


@router.post("/message", response_model=AgentResponse)
async def handle_message(msg: IncomingMessage) -> AgentResponse:
    logger.info("Incoming | channel=%s | session=%s", msg.channel, msg.session_id)
    return await run_agent(msg)


@router.get("/session/{session_id}")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Return stored message history for a session (used by web chat on page load).

    Redis holds the live session (1h TTL). If it has expired — e.g. a customer
    logged out and returns later with the same phone — fall back to Postgres
    so the conversation can still be restored.
    """
    history = await get_session(session_id)
    if history:
        return history

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.timestamp.asc())
    )
    return [{"role": m.role.value, "text": m.text} for m in result.scalars()]
