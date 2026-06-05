# /backend/app/channels_main.py
from fastapi import FastAPI

from app.channels.telegram import router as telegram_router
from app.core.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="MOEI Channels Service", version="0.1.0")
app.include_router(telegram_router)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"channels": "ok"}
