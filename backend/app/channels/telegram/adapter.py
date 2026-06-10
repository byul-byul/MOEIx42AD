# /backend/app/channels/telegram/adapter.py
import httpx
from fastapi import APIRouter, Request, Response
from telegram import Bot, KeyboardButton, ReplyKeyboardMarkup, Update

from app.channels.base import BaseChannel
from app.core.config import settings
from app.core.logger import get_logger
from app.schemas import AgentResponse, IncomingMessage

logger = get_logger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Bot is None when token is not configured (prevents import-time crash)
_bot: Bot | None = Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None


def _detect_language(text: str) -> str:
    return "ar" if any("؀" <= ch <= "ۿ" for ch in text) else "en"


class TelegramChannel(BaseChannel):
    async def parse_incoming(self, raw: dict) -> IncomingMessage | None:
        if _bot is None:
            return None
        update = Update.de_json(raw, _bot)
        message = update.message or update.edited_message
        if not message:
            return None

        # Reply to a shared contact: link this Telegram user to a phone-based
        # Customer (see agent/identity.py) via a normal agent turn.
        if message.contact:
            phone = message.contact.phone_number
            if not phone.startswith("+"):
                phone = f"+{phone}"
            return IncomingMessage(
                session_id=f"telegram_{message.from_user.id}",
                channel="telegram",
                user_id=str(message.from_user.id),
                text="Thanks, here is my phone number for cross-channel support.",
                language="en",
                phone=phone,
            )

        if not message.text:
            return None

        return IncomingMessage(
            session_id=f"telegram_{message.from_user.id}",
            channel="telegram",
            user_id=str(message.from_user.id),
            text=message.text,
            language=_detect_language(message.text),
        )

    async def send_response(self, response: AgentResponse, raw: dict) -> None:
        if _bot is None:
            return
        update = Update.de_json(raw, _bot)
        message = update.message or update.edited_message
        if not message:
            return
        await _bot.send_message(chat_id=message.chat_id, text=response.text)


_channel = TelegramChannel()


@router.post("/webhook")
async def webhook(request: Request) -> Response:
    if _bot is None:
        return Response(status_code=200)

    payload = await request.json()
    logger.info("Telegram update received")

    update = Update.de_json(payload, _bot)
    message = update.message or update.edited_message

    # Onboarding: ask new chats to share their phone number once, so this
    # Telegram user can be linked to the same Customer as WhatsApp/web chat
    # (see agent/identity.py). The button disappears after one tap.
    if message and message.text == "/start":
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share phone number", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await _bot.send_message(
            chat_id=message.chat_id,
            text="Welcome! Please share your phone number so we can recognize "
            "you across channels (WhatsApp, web chat).",
            reply_markup=keyboard,
        )
        return Response(status_code=200)

    incoming = await _channel.parse_incoming(payload)
    if incoming is None:
        return Response(status_code=200)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.backend_url}/api/message",
            json=incoming.model_dump(mode="json"),
        )
        resp.raise_for_status()
        agent_response = AgentResponse(**resp.json())

    await _channel.send_response(agent_response, payload)
    return Response(status_code=200)


@router.post("/setup")
async def setup_webhook() -> dict:
    """Register the Telegram webhook URL with the Bot API. Call once after deploy."""
    if _bot is None:
        return {"status": "error", "detail": "TELEGRAM_BOT_TOKEN not configured"}
    if not settings.telegram_webhook_url:
        return {"status": "error", "detail": "TELEGRAM_WEBHOOK_URL not configured"}

    await _bot.set_webhook(url=settings.telegram_webhook_url)
    logger.info("Telegram webhook set to %s", settings.telegram_webhook_url)
    return {"status": "ok", "webhook_url": settings.telegram_webhook_url}
