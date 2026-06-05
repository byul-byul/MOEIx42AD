# /backend/app/channels/webchat/adapter.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.core import run_agent
from app.core.logger import get_logger
from app.schemas import IncomingMessage

logger = get_logger(__name__)

router = APIRouter(tags=["webchat"])


def _detect_language(text: str) -> str:
    return "ar" if any("؀" <= ch <= "ۿ" for ch in text) else "en"


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    logger.info("WebSocket connected | session=%s", session_id)

    try:
        while True:
            text = await websocket.receive_text()
            if not text.strip():
                continue

            msg = IncomingMessage(
                session_id=session_id,
                channel="webchat",
                user_id=session_id,
                text=text,
                language=_detect_language(text),
            )

            logger.info("WebSocket message | session=%s | text=%.80s", session_id, text)
            response = await run_agent(msg)
            await websocket.send_json(response.model_dump())

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected | session=%s", session_id)
