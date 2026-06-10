# /backend/app/channels_main.py
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.channels.telegram.adapter import router as telegram_router
from app.channels.voice.adapter import router as voice_router
from app.channels.whatsapp.adapter import router as whatsapp_router
from app.core.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="MOEI Channels Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telegram_router)
app.include_router(voice_router)
app.include_router(whatsapp_router)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"channels": "ok"}
