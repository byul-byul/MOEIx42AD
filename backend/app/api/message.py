# /backend/app/api/message.py
from fastapi import APIRouter

from app.agent.core import run_agent
from app.core.logger import get_logger
from app.schemas import AgentResponse, IncomingMessage

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])


@router.post("/message", response_model=AgentResponse)
async def handle_message(msg: IncomingMessage) -> AgentResponse:
    logger.info("Incoming | channel=%s | session=%s", msg.channel, msg.session_id)
    return await run_agent(msg)
