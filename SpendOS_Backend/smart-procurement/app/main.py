import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import init_db, get_db
from app.api.procurement_routes import router as procurement_router
from app.api.auth_routes import router as auth_router
from fastapi import FastAPI, Request, Depends

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Smart Procurement Platform...")
    logger.info("✅ Configuration validated — all required secrets are present.")
    await init_db()
    logger.info("Connecting to Redis for ARQ task queue...")
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    logger.info("ARQ Redis pool ready.")
    yield
    await app.state.arq_pool.close()
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered procurement intelligence platform. "
        "Discovers, enriches, scores and ranks vendors using LangGraph + Groq."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middlewares
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Forwarded headers (Trusted Proxy) - Mandatory for Render load balancers
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.trusted_hosts_list)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Set-Cookie"],
)


# ── Global Exception Handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(procurement_router)


@app.get("/health", tags=["Health"])
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Deep health check endpoint for monitoring and CI/CD."""
    health_status = "ok"
    db_status = "connected"
    redis_status = "connected"

    # 1. Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check: Database connection failed: {e}")
        db_status = "error"
        health_status = "degraded"

    # 2. Check Redis (ARQ Pool)
    try:
        # ARQ's pool (RedisPool) has an underlying redis connection we can ping
        # via the handle or just a simple operation.
        await request.app.state.arq_pool.all_job_definitions()
    except Exception as e:
        logger.error(f"Health check: Redis connection failed: {e}")
        redis_status = "error"
        health_status = "degraded"

    return {
        "status": health_status,
        "database": db_status,
        "redis": redis_status,
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
