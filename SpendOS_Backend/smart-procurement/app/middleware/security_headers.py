"""
Security headers middleware for SpendOS.

Adds standard HTTP security headers to every response to protect against
common web vulnerabilities (clickjacking, MIME sniffing, XSS, etc.).

Reference: https://owasp.org/www-project-secure-headers/
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects security-hardening HTTP headers into every response.

    Headers Included:
        - X-Content-Type-Options: nosniff — prevents MIME-type sniffing.
        - X-Frame-Options: DENY — blocks clickjacking via iframes.
        - X-XSS-Protection: 1; mode=block — legacy XSS filter (belt-and-braces).
        - Referrer-Policy: strict-origin-when-cross-origin — controls Referer leakage.
        - Permissions-Policy — disables unused browser APIs (camera, microphone, etc.).
        - Strict-Transport-Security — enforces HTTPS for 1 year with subdomains.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        return response
