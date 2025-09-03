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
    PaperListItemResponse,
    PaperListLightweightResponse,
    PaperListResponse,
    PaperResponse,
    StarredPapersResponse,
    StarResponse,
    SummaryDetailResponse,
    SummaryReadResponse,
)
from core.models.api.streaming import (
    StreamingCompleteEvent,
    StreamingErrorEvent,
    StreamingStatusEvent,
)

# Batch models
from core.models.batch import (
    BatchActionResponse,
    BatchDetailsResponse,
    BatchListResponse,
    BatchRequestEntry,
    BatchRequestPayload,
    BatchResponseBase,
    BatchResult,
    BatchStatusResponse,
    PendingSummariesResponse,
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
    PaperBase,
    Summary,
    User,
    UserInterest,
    UserStar,
)

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
    "PaperListLightweightResponse",
    "PaperListItemResponse",
    "PaperDeleteResponse",
    "CategoriesResponse",
    "SummaryDetailResponse",
    "SummaryReadResponse",
    "AuthError",
    "StreamingStatusEvent",
    "StreamingCompleteEvent",
    "StreamingErrorEvent",
    "StarResponse",
    "StarredPapersResponse",
    # Database models (SQLModel rows)
    "Paper",
    "PaperBase",
    "Summary",
    "User",
    "UserInterest",
    "UserStar",
    "FeedItem",
    "CrawlEvent",
    "LLMRequest",
    # Batch models
    "BatchActionResponse",
    "BatchDetailsResponse",
    "BatchListResponse",
    "BatchRequestEntry",
    "BatchRequestPayload",
    "BatchResult",
    "BatchResponseBase",
    "BatchStatusResponse",
    "PendingSummariesResponse",
    # External models
    "OpenAIMessage",
    "OpenAITool",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "PaperAnalysis",
]
