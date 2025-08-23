"""Web crawler and summarizer package."""

from .summarizer import (
    AbstractSummarizer,
    SummaryRequest,
    SummaryResponse,
)
from .summarizer.service import SummarizationService

__all__ = [
    "AbstractSummarizer",
    "SummaryRequest",
    "SummaryResponse",
    "SummarizationService",
]
