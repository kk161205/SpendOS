"""
Rate limiting configuration for SpendOS API.

Uses SlowAPI (a wrapper around limits) to throttle requests per-user
and protect against brute-force and abuse.

Rate limits are applied per-endpoint using decorators, and a global
default is set via the middleware.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request
from app.config import get_settings

settings = get_settings()


def _get_rate_limit_key(request: Request) -> str:
    """
    Derive the rate-limit key from the authenticated user (if available),
    falling back to the client IP address.

    This ensures that:
      - Authenticated users are limited per-account (fair across shared IPs).
      - Unauthenticated requests (login, register) are limited per-IP.
    """
    # Try to extract user from a previously-decoded JWT cookie/header
    user_id = None
    try:
        # Check if auth info was attached by the dependency
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
    except Exception:
        pass

    if user_id:
        return f"user:{user_id}"

    return get_remote_address(request)


# Global limiter instance — imported by main.py and route files
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    storage_uri=settings.redis_url,
)
