from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from config import settings
from app.utils.logger import setup_logger
from app.core.redis_client import redis_client

from app.api import books, reading, ambiance, admin, library, me, leaderboard, discovery
from app.middleware.rate_limit import limiter, custom_rate_limit_handler

# Setup logging
logger = setup_logger("vibetale")

app = FastAPI(
    title="VibeTale Backend API",
    description="Backend API for immersive e-book reading experience",
    version="1.0.0"
)

# Add rate limiter to state and register exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


@app.on_event("startup")
async def startup_event():
    """Sync audit_enabled: Redis is source of truth; fallback to settings if Redis empty."""
    redis_val = await redis_client.get("audit_enabled")
    if redis_val is not None:
        settings.audit_enabled = redis_val == "true"
        logger.info(f"Startup: audit_enabled loaded from Redis = {settings.audit_enabled}")
    else:
        await redis_client.set("audit_enabled", str(settings.audit_enabled).lower())
        logger.info(f"Startup: audit_enabled synced to Redis = {settings.audit_enabled}")

# CORS middleware for Flutter mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(books.router)
app.include_router(reading.router)
app.include_router(ambiance.router)
app.include_router(admin.router)
app.include_router(library.router)
app.include_router(me.router)
app.include_router(leaderboard.router)
app.include_router(discovery.router)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "VibeTale Backend API", "status": "running"}


@app.get("/health")
async def health_check():
    logger.debug("Health check endpoint accessed")
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
