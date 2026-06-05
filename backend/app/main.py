# /backend/app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import Base, check_db, engine
from app.core.logger import get_logger
from app.core.redis import check_redis
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
