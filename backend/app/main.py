# /backend/app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.message import router as message_router
from app.channels.webchat.adapter import router as webchat_router
from app.core.database import Base, check_db, engine
from app.core.logger import get_logger
from app.core.redis import check_redis
from app.dashboard.metrics import router as metrics_router
from app.schemas import HealthResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (Alembic handles migrations in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    yield
    await engine.dispose()
    logger.info("Backend shut down")


app = FastAPI(title="MOEI Agent Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(message_router)
app.include_router(webchat_router)
app.include_router(metrics_router)


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    """
    All three statuses must be 'ok' before starting new feature work.
    See CLAUDE.md — HEALTH CHECK section.
    """
    redis_status, db_status = await check_redis(), await check_db()
    overall = HealthResponse(backend="ok", redis=redis_status, db=db_status)
    logger.info("Health check: %s", overall.model_dump())
    return overall
