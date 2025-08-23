"""API models package."""

from .paper import PaperCreate, PaperDeleteResponse, PaperResponse

__all__ = [
    "PaperCreate",
    "PaperResponse",
    "PaperDeleteResponse",
]
