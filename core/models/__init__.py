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
    StarredPapersResponse,
    StarResponse,
    SummaryReadResponse,
)
from core.models.api.streaming import (
    StreamingCompleteEvent,
    StreamingErrorEvent,
    StreamingStatusEvent,
)

# Database models (먼저 로드 - 다른 모델들이 의존함)
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
