"""Repository layer for database operations."""

from sqlmodel import Session

# SQLModel repositories
from .llm_batch import LLMBatchRepository
from .paper import PaperRepository
from .summary import SummaryRepository
from .summary_read import SummaryReadRepository
from .user import (
    UserInterestRepository,
    UserRepository,
    UserStarRepository,
)

__all__ = [
    "PaperRepository",
    "SummaryRepository",
    "SummaryReadRepository",
    "UserRepository",
    "UserInterestRepository",
    "UserStarRepository",
    "LLMBatchRepository",
]
