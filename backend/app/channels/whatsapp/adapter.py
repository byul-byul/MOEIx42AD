# /backend/app/channels/whatsapp/adapter.py
import httpx
from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse

from app.channels.base import BaseChannel
from app.core.config import settings
from app.core.logger import get_logger
from app.schemas import AgentResponse, IncomingMessage

logger = get_logger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _detect_language(text: str) -> str:
    return "ar" if any("؀" <= ch <= "ۿ" for ch in text) else "en"


class WhatsAppChannel(BaseChannel):
    async def parse_incoming(self, raw: dict) -> IncomingMessage | None:
        body = raw.get("Body", "").strip()
        from_ = raw.get("From", "")  # Twilio sends "whatsapp:+9715..."
        if not body or not from_:
            return None

        phone = from_.removeprefix("whatsapp:")
        return IncomingMessage(
            session_id=f"whatsapp_{phone}",
            channel="whatsapp",
            user_id=phone,
            text=body,
            language=_detect_language(body),
            phone=phone,
        )

    async def send_response(self, response: AgentResponse, raw: dict) -> None:
        # No-op: the reply is delivered synchronously via the TwiML response
        # to the webhook request, same as Twilio's own messaging convention.
        pass


_channel = WhatsAppChannel()


@router.post("/webhook")
async def webhook(From: str = Form(...), Body: str = Form("")) -> Response:
    """Twilio WhatsApp Sandbox webhook — replies synchronously via TwiML."""
    logger.info("WhatsApp message received | from=%s", From)

    incoming = await _channel.parse_incoming({"From": From, "Body": Body})

    twiml = MessagingResponse()
    if incoming is None:
        return Response(content=str(twiml), media_type="application/xml")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.backend_url}/api/message",
            json=incoming.model_dump(mode="json"),
        )
        resp.raise_for_status()
        agent_response = AgentResponse(**resp.json())

    twiml.message(agent_response.text)
    return Response(content=str(twiml), media_type="application/xml")
