"""Web crawler and summarizer package."""

from .summarizer import (
    AbstractSummarizer,
    StructuredSummary,
    SummaryRequest,
    SummaryResponse,
)
from .summarizer.service import SummarizationService

__all__ = [
    "AbstractSummarizer",
    "StructuredSummary",
    "SummaryRequest",
    "SummaryResponse",
    "SummarizationService",
]
