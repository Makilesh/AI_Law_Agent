"""
Security Middleware - FastAPI middleware for comprehensive security.

Integrates rate limiting, IP blocking, and request validation
into a single middleware that processes all incoming requests.
"""

import logging
import time
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from security.rate_limiter import get_rate_limiter
from security.ip_blocker import get_ip_blocker
from security.request_validator import get_request_validator

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware for FastAPI.

    Performs:
    - IP blocking checks
    - Rate limiting
    - Request validation
    - Security headers
    """

    def __init__(
        self,
        app: ASGIApp,
        enable_rate_limiting: bool = True,
        enable_ip_blocking: bool = True,
        enable_request_validation: bool = True,
        excluded_paths: list = None
    ):
        """
        Initialize security middleware.

        Args:
            app: FastAPI application
            enable_rate_limiting: Enable rate limiting (default: True)
            enable_ip_blocking: Enable IP blocking (default: True)
            enable_request_validation: Enable request validation (default: True)
            excluded_paths: List of paths to exclude from security checks
        """
        super().__init__(app)
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_ip_blocking = enable_ip_blocking
        self.enable_request_validation = enable_request_validation

        # Paths that bypass security checks
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/favicon.ico"
        ]

        # Initialize components
        self.rate_limiter = get_rate_limiter()
        self.ip_blocker = get_ip_blocker()
        self.request_validator = get_request_validator()

        logger.info("SecurityMiddleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request through security checks.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint

        Returns:
            HTTP response
        """
        start_time = time.time()

        try:
            # Skip security checks for excluded paths
            if self._is_excluded_path(request.url.path):
                response = await call_next(request)
                return response

            # Get client IP
            client_ip = self._get_client_ip(request)

            # 1. Check if IP is whitelisted (bypass all checks)
            if self.enable_ip_blocking and self.ip_blocker.is_whitelisted(client_ip):
                logger.debug(f"✅ Whitelisted IP: {client_ip}")
                response = await call_next(request)
                return self._add_security_headers(response, {"whitelisted": True})

            # 2. Check if IP is blocked
            if self.enable_ip_blocking and self.ip_blocker.is_blocked(client_ip):
                block_info = self.ip_blocker.get_block_info(client_ip)
                logger.warning(f"🚫 Blocked IP attempted access: {client_ip}")

                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Access forbidden",
                        "message": "Your IP address has been blocked",
                        "reason": block_info.get("reason", "abuse") if block_info else "abuse",
                        "blocked_at": block_info.get("blocked_at") if block_info else None
                    }
                )

            # 3. Rate limiting check
            if self.enable_rate_limiting:
                endpoint = f"{request.method}:{request.url.path}"
                allowed, limit_info = self.rate_limiter.is_allowed(client_ip, endpoint)

                if not allowed:
                    logger.warning(
                        f"⚠️ Rate limit exceeded: {client_ip} - {endpoint}"
                    )

                    # Auto-block IP after excessive violations (optional)
                    violations = limit_info.get("violations", 0)
                    if violations >= 3:  # Block after 3 violations
                        self.ip_blocker.block_ip(
                            client_ip,
                            reason="excessive_rate_limit_violations",
                            duration_hours=1
                        )
                        logger.warning(f"🚫 Auto-blocked IP due to violations: {client_ip}")

                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": "Rate limit exceeded",
                            "message": "Too many requests. Please try again later.",
                            "retry_after": limit_info.get("retry_after", 60)
                        },
                        headers={
                            "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(limit_info.get("reset_at", 0)),
                            "Retry-After": str(limit_info.get("retry_after", 60))
                        }
                    )

            # 4. Request validation (for POST requests with body)
            if self.enable_request_validation and request.method == "POST":
                # Note: Full body validation would require reading the body
                # which can interfere with FastAPI's request handling.
                # This is a simplified check - detailed validation happens in endpoints.

                # Validate content type
                content_type = request.headers.get("content-type", "")
                if content_type and "application/json" not in content_type.lower():
                    if "multipart/form-data" not in content_type.lower():
                        logger.warning(f"⚠️ Invalid content type from {client_ip}: {content_type}")

            # Process request
            response = await call_next(request)

            # Add security headers
            response = self._add_security_headers(response, {
                "rate_limit": limit_info if self.enable_rate_limiting else None
            })

            # Log processing time
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = f"{process_time:.3f}"

            return response

        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            # On error, allow request to proceed (fail-open)
            response = await call_next(request)
            return response

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.

        Checks X-Forwarded-For header first (for proxies),
        then falls back to direct client IP.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (Nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from security checks.

        Args:
            path: Request path

        Returns:
            True if excluded, False otherwise
        """
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False

    def _add_security_headers(self, response: Response, metadata: dict = None) -> Response:
        """
        Add security headers to response.

        Args:
            response: HTTP response
            metadata: Additional metadata (rate limit info, etc.)

        Returns:
            Response with security headers
        """
        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Rate limit headers
        if metadata and metadata.get("rate_limit"):
            limit_info = metadata["rate_limit"]
            response.headers["X-RateLimit-Limit"] = str(limit_info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(limit_info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(limit_info.get("reset_at", 0))

        # Whitelisted indicator
        if metadata and metadata.get("whitelisted"):
            response.headers["X-Security-Bypass"] = "whitelisted"

        return response


def create_security_middleware(
    app: ASGIApp,
    enable_rate_limiting: bool = True,
    enable_ip_blocking: bool = True,
    enable_request_validation: bool = True
) -> SecurityMiddleware:
    """
    Factory function to create security middleware.

    Args:
        app: FastAPI application
        enable_rate_limiting: Enable rate limiting
        enable_ip_blocking: Enable IP blocking
        enable_request_validation: Enable request validation

    Returns:
        Configured SecurityMiddleware instance
    """
    return SecurityMiddleware(
        app=app,
        enable_rate_limiting=enable_rate_limiting,
        enable_ip_blocking=enable_ip_blocking,
        enable_request_validation=enable_request_validation
    )
