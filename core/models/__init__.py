"""Unified models package for theark system.

This package consolidates all Pydantic models used throughout the application
into a well-organized structure that reduces duplication and improves maintainability.
"""

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
)
from core.models.api.streaming import (
    StreamingCompleteEvent,
    StreamingErrorEvent,
    StreamingEvent,
    StreamingStatusEvent,
)

# Database models
from core.models.database.entities import (
    CrawlEvent,
    FeedItem,
    PaperEntity,
    SummaryEntity,
    UserEntity,
    UserInterestEntity,
    UserStarEntity,
)
from core.models.database.tracking import LLMRequest, LLMUsageStats

# Domain models (core business logic)
from core.models.domain.paper import Paper, PaperMetadata
from core.models.domain.summary import Summary, SummaryContent
from core.models.domain.task import TaskManagerStatus, TaskStats
from core.models.domain.user import User, UserInterest, UserStar

# External API models
from core.models.external.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIMessage,
    OpenAITool,
    PaperAnalysis,
)

__all__ = [
    # Domain models
    "Paper",
    "PaperMetadata",
    "Summary",
    "SummaryContent",
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
    "AuthError",
    "StreamingEvent",
    "StreamingStatusEvent",
    "StreamingCompleteEvent",
    "StreamingErrorEvent",
    # Database models
    "PaperEntity",
    "SummaryEntity",
    "UserEntity",
    "UserInterestEntity",
    "UserStarEntity",
    "FeedItem",
    "CrawlEvent",
    "LLMRequest",
    "LLMUsageStats",
    # External models
    "OpenAIMessage",
    "OpenAITool",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "PaperAnalysis",
]
