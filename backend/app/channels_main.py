# /backend/app/channels_main.py
from fastapi import FastAPI

from app.core.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="MOEI Channels Service", version="0.1.0")


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"channels": "ok"}
