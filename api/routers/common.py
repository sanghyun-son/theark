"""Common API endpoints router."""

import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from core import get_logger
from core.config import load_settings

logger = get_logger(__name__)

router = APIRouter(tags=["common"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    timestamp: str


@router.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Root endpoint with basic API information."""
    # Load HTML template
    template_path = Path("templates", "root.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    current_settings = load_settings()
    return HealthResponse(
        status="healthy",
        version=current_settings.api_version,
        timestamp=datetime.datetime.now().isoformat(),
    )


class TestAuthResponse(BaseModel):
    """Test authentication response model."""

    message: str
    environment: str
    auth_required: bool
    auth_header_present: bool
    auth_header_value: str | None


@router.get("/test-auth", response_model=TestAuthResponse)
async def test_auth(request: Request) -> TestAuthResponse:
    """Test authentication endpoint - shows current auth status."""
    current_settings = load_settings()

    # Check authentication if required
    if current_settings.auth_required:
        auth_header = request.headers.get(current_settings.auth_header_name)
        if not auth_header or not auth_header.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "detail": "Authentication required",
                    "error": "missing_auth_header",
                    "environment": current_settings.environment.value,
                },
            )

    auth_header = request.headers.get(current_settings.auth_header_name)

    return TestAuthResponse(
        message="Authentication test endpoint",
        environment=current_settings.environment.value,
        auth_required=current_settings.auth_required,
        auth_header_present=auth_header is not None,
        auth_header_value=auth_header,
    )


@router.get("/favicon.ico", response_model=None)
async def favicon() -> HTMLResponse | FileResponse:
    """Favicon endpoint - returns the favicon.ico file."""
    # Get the favicon path
    favicon_path = Path("static/favicon.ico")

    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/x-icon")
    else:
        # Return a simple placeholder if favicon doesn't exist
        placeholder_content = "<!-- Placeholder favicon -->"
        return HTMLResponse(
            content=placeholder_content,
            status_code=200,
            headers={"Content-Type": "text/html"},
        )
