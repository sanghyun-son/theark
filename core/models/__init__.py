"""Unified models package for theark system."""

# API models (request/response)
from core.models.api.requests import (
    PaperCreateRequest,
    PaperListRequest,
)
from core.models.api.responses import (
    AuthError,
    CategoriesResponse,
    PaperDeleteResponse,
    PaperListResponse,
    PaperResponse,
    StarredPapersResponse,
    StarResponse,
    SummaryReadResponse,
)
from core.models.api.streaming import (
    StreamingCompleteEvent,
    StreamingErrorEvent,
    StreamingStatusEvent,
)

# Domain models (core business logic)
from core.models.domain.task import TaskManagerStatus, TaskStats

# External API models
from core.models.external.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIMessage,
    OpenAITool,
    PaperAnalysis,
)

# Database models (SQLModel rows)
from core.models.rows import (
    CrawlEvent,
    FeedItem,
    LLMRequest,
    Paper,
    Summary,
    User,
    UserInterest,
    UserStar,
)

# Summarization models
from core.models.summarization import SummaryRequest, SummaryResponse

__all__ = [
    # Domain models
    "User",
    "UserInterest",
    "UserStar",
    "TaskStats",
    "TaskManagerStatus",
    # API models
    "PaperCreateRequest",
    "PaperListRequest",
    "PaperResponse",
    "PaperListResponse",
    "PaperDeleteResponse",
    "CategoriesResponse",
    "SummaryReadResponse",
    "AuthError",
    "StreamingStatusEvent",
    "StreamingCompleteEvent",
    "StreamingErrorEvent",
    "StarResponse",
    "StarredPapersResponse",
    # Database models (SQLModel rows)
    "Paper",
    "Summary",
    "User",
    "UserInterest",
    "UserStar",
    "FeedItem",
    "CrawlEvent",
    "LLMRequest",
    # External models
    "OpenAIMessage",
    "OpenAITool",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "PaperAnalysis",
    # Summarization models
    "SummaryRequest",
    "SummaryResponse",
]
