"""Domain models for LLM usage statistics."""

from pydantic import BaseModel, Field


class ModelUsageStats(BaseModel):
    """Statistics for a specific LLM model."""

    total_requests: int = Field(default=0, description="Total number of requests")
    successful_requests: int = Field(
        default=0, description="Number of successful requests"
    )
    failed_requests: int = Field(default=0, description="Number of failed requests")
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD")
    avg_response_time_ms: float = Field(
        default=0.0, description="Average response time in milliseconds"
    )


class CostSummary(BaseModel):
    """Cost summary for a specific date."""

    total_cost_usd: float = Field(description="Total cost in USD")
    request_count: int = Field(description="Number of requests")
    date: str = Field(description="Date in YYYY-MM-DD format")


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics."""

    models: dict[str, ModelUsageStats] = Field(description="Statistics by model")
    total_requests: int = Field(description="Total requests across all models")
    total_cost_usd: float = Field(description="Total cost across all models")
    period: dict[str, str] = Field(description="Start and end dates")
