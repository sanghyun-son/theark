"""Authentication middleware for the theark system."""

from typing import Any, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.models.auth import AuthError
from core.config import settings
from core.log import get_logger

logger = get_logger(__name__)


class AuthMiddleware:
    """Authentication middleware that checks for auth headers based on environment."""

    def __init__(self, app: Callable[..., Any]) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Any],
        send: Callable[..., Any],
    ) -> None:
        """Process the request through authentication middleware."""
        # Early exit for non-HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        if self._should_skip_auth(request):
            await self.app(scope, receive, send)
            return

        if not settings.auth_required:
            await self.app(scope, receive, send)
            return

        if self._has_auth_header(request):
            await self.app(scope, receive, send)
            return

        logger.warning(f"Missing auth header in {settings.environment} mode")
        response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=AuthError(
                detail="Authentication required",
                error="missing_auth_header",
                environment=settings.environment.value,
            ),
        )
        await response(scope, receive, send)

    def _should_skip_auth(self, request: Request) -> bool:
        """Check if authentication should be skipped for this request."""
        path = request.url.path
        if path.startswith("/static/"):
            return True

        skip_paths = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
        }
        return path in skip_paths

    def _has_auth_header(self, request: Request) -> bool:
        """Check if the request has the required authentication header."""
        auth_header = request.headers.get(settings.auth_header_name)
        return auth_header is not None and auth_header.strip() != ""


def get_auth_middleware() -> type[AuthMiddleware] | None:
    """Get authentication middleware if required."""
    if settings.auth_required:
        logger.info(f"Middleware enabled for {settings.environment} mode")
        return AuthMiddleware

    logger.info(f"Middleware disabled for {settings.environment} mode")
    return None
