"""Paper abstract summarizer module."""

# Export models for external use
from core.models.external.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIMessage,
    OpenAIPropertyDefinition,
    OpenAITool,
    PaperAnalysis,
)

from .openai_summarizer import OpenAISummarizer
from .summarizer import (
    AbstractSummarizer,
    SummaryRequest,
    SummaryResponse,
)

__all__ = [
    "AbstractSummarizer",
    "SummaryRequest",
    "SummaryResponse",
    "OpenAISummarizer",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "OpenAIMessage",
    "OpenAIPropertyDefinition",
    "OpenAITool",
    "PaperAnalysis",
]
