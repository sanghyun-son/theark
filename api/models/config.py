"""Configuration models for API responses."""

from pydantic import BaseModel


class CategoriesResponse(BaseModel):
    """Response model for preset categories."""

    categories: list[str]
    count: int
