# /backend/app/api/message.py
from fastapi import APIRouter

from app.agent.core import run_agent
from app.core.logger import get_logger
from app.core.redis import get_session
from app.schemas import AgentResponse, IncomingMessage

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])


@router.post("/message", response_model=AgentResponse)
async def handle_message(msg: IncomingMessage) -> AgentResponse:
    logger.info("Incoming | channel=%s | session=%s", msg.channel, msg.session_id)
    return await run_agent(msg)


@router.get("/session/{session_id}")
async def get_session_history(session_id: str) -> list[dict]:
    """Return stored message history for a session (used by web chat on page load)."""
    return await get_session(session_id)
