"""SpendOS — FastAPI application entry point.

Sets up middleware (CORS, security headers, rate limiting, proxy headers),
registers API routers, and manages the lifecycle of external resources
(Redis/ARQ pool).
"""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.auth_routes import router as auth_router
from app.api.procurement_routes import router as procurement_router
from app.config import get_settings
from app.database import engine
from app.middleware.rate_limit import limiter, _rate_limit_exceeded_handler
from app.middleware.security_headers import SecurityHeadersMiddleware

# ── Logging Configuration ─────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Lifespan Management ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown of external resources.
    1. Initialize Redis connection pool for ARQ.
    2. Gracefully close connections on shutdown.
    """
    settings = get_settings()
    logger.info("Starting up: initializing ARQ/Redis pool...")
    
    # Initialize ARQ Redis pool
    try:
        app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        logger.info("ARQ/Redis pool connected.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis/ARQ: {e}")
        # In production, this might be a fatal error
    
    yield
    
    # Shutdown
    if hasattr(app.state, "arq_pool"):
        logger.info("Shutting down: closing ARQ/Redis pool...")
        await app.state.arq_pool.close()
        logger.info("Pool closed.")

# ── App Initialization ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Procurement Platform",
    description="Automated vendor discovery and risk analysis using LangGraph and LangChain.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware (applied in REVERSE order — last added runs first) ──────────────
settings = get_settings()

# 1. CORS — must be the outermost middleware to handle preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origins_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Security Headers (X-Content-Type-Options, X-Frame-Options, HSTS, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# 3. Rate Limiting (SlowAPI — uses Redis as backend)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 4. Proxy Headers (for Render/Cloudflare reverse proxies)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.trusted_hosts_list)


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
):
    """Simple health check including DB connectivity."""
    status = {"status": "ok", "services": {"api": "up"}}
    
    # Test DB connection
    try:
        from sqlalchemy import text
        from app.database import get_db
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            status["services"]["database"] = "up"
            break
    except Exception as e:
        logger.error(f"Health check: Database connection failed: {e}")
        status["services"]["database"] = "down"
        status["status"] = "degraded"

    # 2. Test ARQ/Redis connection
    if hasattr(request.app.state, "arq_pool"):
        try:
            # Simple check to see if the pool is responsive
            await request.app.state.arq_pool.all_job_definitions()
            status["services"]["redis"] = "up"
        except Exception as e:
            logger.error(f"Health check: Redis/ARQ connection failed: {e}")
            status["services"]["redis"] = "down"
            status["status"] = "degraded"
    else:
        status["services"]["redis"] = "not_initialized"
        status["status"] = "degraded"

    return status

@app.get("/", tags=["Info"])
async def root():
    return {
        "message": "Welcome to SpendOS Smart Procurement API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
