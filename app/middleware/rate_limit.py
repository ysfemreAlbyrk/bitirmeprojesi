"""Rate limiting middleware using slowapi"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.utils.logger import get_logger

logger = get_logger("vibetale")

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors"""
    logger.warning(f"Rate limit exceeded for {request.client.host}: {exc.detail}")
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded",
            "error": str(exc.detail),
            "retry_after": exc.retry_after
        },
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(exc.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(exc.reset)
        }
    )


# Override the default handler
limiter._rate_limit_exceeded_handler = custom_rate_limit_handler
