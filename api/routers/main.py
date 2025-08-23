"""Main page router."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Templates directory
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request) -> HTMLResponse:
    """Serve the main page."""
    return templates.TemplateResponse(request, "index.html")
