"""User domain models."""

from pydantic import BaseModel, Field, field_validator

# Default user ID for testing and development
DEFAULT_USER_ID = 1


class User(BaseModel):
    """Application user model."""

    user_id: int | None = None
    email: str = Field(..., description="User email address")
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower()


class UserInterest(BaseModel):
    """User interest model."""

    user_id: int = Field(..., gt=0)
    kind: str = Field(..., description="Interest kind (category, keyword, author)")
    value: str = Field(..., min_length=1)
    weight: float = Field(default=1.0, ge=0.0, le=10.0)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        """Validate interest kind."""
        valid_kinds = {"category", "keyword", "author"}
        if v not in valid_kinds:
            raise ValueError(f"Invalid kind. Must be one of: {valid_kinds}")
        return v


class UserStar(BaseModel):
    """User star/bookmark model."""

    user_id: int = Field(..., gt=0)
    paper_id: int = Field(..., gt=0)
    note: str | None = None
    created_at: str | None = None
