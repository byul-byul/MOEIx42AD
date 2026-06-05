# /backend/app/channels/voice/adapter.py
import base64

import httpx
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.schemas import AgentResponse, IncomingMessage

logger = get_logger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

_openai = AsyncOpenAI(api_key=settings.openai_api_key)

# ElevenLabs voice ID can be configured later; OpenAI TTS used by default
_TTS_VOICE = "nova"  # alloy | echo | fable | onyx | nova | shimmer


def _detect_language(text: str) -> str:
    return "ar" if any("؀" <= ch <= "ۿ" for ch in text) else "en"


@router.post("/message")
async def voice_message(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
) -> JSONResponse:
    """
    Accepts a voice recording, runs it through STT → agent → TTS,
    and returns transcript + agent text + base64 audio in one response.
    """
    logger.info("Voice message received | session=%s | content_type=%s", session_id, audio.content_type)

    # 1. STT — OpenAI Whisper
    audio_bytes = await audio.read()
    try:
        transcript_obj = await _openai.audio.transcriptions.create(
            model="whisper-1",
            file=(audio.filename or "recording.webm", audio_bytes, audio.content_type or "audio/webm"),
        )
        transcript = transcript_obj.text.strip()
    except Exception as exc:
        logger.error("Whisper STT failed: %s", exc)
        return JSONResponse(status_code=502, content={"error": f"STT failed: {exc}"})

    logger.info("Transcript | session=%s | text=%.80s", session_id, transcript)

    # 2. Agent
    incoming = IncomingMessage(
        session_id=session_id,
        channel="voice",
        user_id=session_id,
        text=transcript,
        language=_detect_language(transcript),
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.backend_url}/api/message",
                json=incoming.model_dump(mode="json"),
            )
            resp.raise_for_status()
            agent_response = AgentResponse(**resp.json())
    except Exception as exc:
        logger.error("Agent call failed: %s", exc)
        return JSONResponse(status_code=502, content={"error": f"Agent failed: {exc}"})

    # 3. TTS — OpenAI
    try:
        tts = await _openai.audio.speech.create(
            model="tts-1",
            voice=_TTS_VOICE,
            input=agent_response.text,
        )
        audio_b64 = base64.b64encode(tts.content).decode()
    except Exception as exc:
        logger.error("TTS failed: %s — returning text only", exc)
        audio_b64 = None

    return JSONResponse(content={
        "transcript": transcript,
        "agent": agent_response.model_dump(),
        "audio_base64": audio_b64,
    })
