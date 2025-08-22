"""Abstract summarizer implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .models import PaperAnalysisData


class StructuredSummary(PaperAnalysisData):
    """Structured summary extracted from paper abstract."""

    pass


@dataclass
class SummaryRequest:
    """Request for abstract summarization."""

    custom_id: str
    content: str  # The abstract content
    language: str = "English"
    interest_section: str = ""
    use_tools: bool = True
    model: str = "gpt-4o-mini"


@dataclass
class SummaryResponse:
    """Response from abstract summarization."""

    custom_id: str
    summary: str | None = None  # For non-structured responses
    structured_summary: StructuredSummary | None = None  # For tool-based responses
    original_length: int = 0
    summary_length: int = 0
    metadata: dict[str, Any] | None = None


class AbstractSummarizer(ABC):
    """Abstract base class for paper abstract summarizers."""

    @abstractmethod
    async def summarize(self, request: SummaryRequest) -> SummaryResponse:
        """Summarize the given abstract."""
        pass
