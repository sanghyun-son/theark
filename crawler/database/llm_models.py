"""Database models for LLM request tracking."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LLMRequest(BaseModel):
    """LLM request tracking model."""

    request_id: int | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of the request",
    )
    model: str = Field(..., description="LLM model used (e.g., gpt-4o-mini)")
    provider: str = Field(
        default="openai", description="LLM provider (openai, anthropic, etc.)"
    )
    endpoint: str = Field(
        default="/v1/chat/completions", description="API endpoint called"
    )

    # Request metadata
    is_batched: bool = Field(
        default=False, description="Whether this was a batch request"
    )
    request_type: str = Field(
        default="chat",
        description="Type of request (chat, completion, embedding)",
    )
    custom_id: str | None = Field(
        default=None, description="Custom ID for tracking specific operations"
    )

    # Token usage
    prompt_tokens: int | None = Field(default=None, description="Tokens in the prompt")
    completion_tokens: int | None = Field(
        default=None, description="Tokens in the completion"
    )
    total_tokens: int | None = Field(default=None, description="Total tokens used")

    # Performance metrics
    response_time_ms: int | None = Field(
        default=None, description="Response time in milliseconds"
    )

    # Status and error tracking
    status: str = Field(
        default="pending",
        description="Request status (pending, success, error)",
    )
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    http_status_code: int | None = Field(default=None, description="HTTP status code")

    # Cost tracking (optional)
    estimated_cost_usd: float | None = Field(
        default=None, description="Estimated cost in USD"
    )

    # Additional metadata
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional request metadata"
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("Invalid timestamp format. Use ISO format.")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        valid_statuses = {"pending", "success", "error", "timeout", "cancelled"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v

    def calculate_cost(self) -> float:
        """Calculate the estimated cost based on OpenAI's current pricing.

        Based on https://platform.openai.com/docs/pricing?latest-pricing=standard
        Only text tokens are considered. Batch processing is 50% of regular pricing.

        Returns:
            Estimated cost in USD
        """
        if not self.prompt_tokens or not self.completion_tokens:
            return 0.0

        # OpenAI pricing per 1M tokens (as of 2024)
        # Source: https://platform.openai.com/docs/pricing?latest-pricing=standard
        pricing: dict[str, dict[str, float]] = {
            # GPT-5 models
            "gpt-5": {"input": 1.25, "output": 10.00},
            "gpt-5-mini": {"input": 0.25, "output": 2.00},
            "gpt-5-nano": {"input": 0.05, "output": 0.40},
            "gpt-5-chat-latest": {"input": 1.25, "output": 10.00},
            "gpt-4.1": {"input": 2.00, "output": 8.00},
            "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
            "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00},
            "gpt-4o-audio-preview": {"input": 2.50, "output": 10.00},
            "gpt-4o-realtime-preview": {"input": 5.00, "output": 20.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o-mini-audio-preview": {"input": 0.15, "output": 0.60},
            "gpt-4o-mini-realtime-preview": {"input": 0.60, "output": 2.40},
            "gpt-4o-search-preview": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini-search-preview": {"input": 0.15, "output": 0.60},
            "o1": {"input": 15.00, "output": 60.00},
            "o1-pro": {"input": 150.00, "output": 600.00},
            "o1-mini": {"input": 1.10, "output": 4.40},
            "o3": {"input": 2.00, "output": 8.00},
            "o3-pro": {"input": 20.00, "output": 80.00},
            "o3-mini": {"input": 1.10, "output": 4.40},
            "o3-deep-research": {"input": 10.00, "output": 40.00},
            "o4-mini": {"input": 1.10, "output": 4.40},
            "o4-mini-deep-research": {"input": 2.00, "output": 8.00},
            "codex-mini-latest": {"input": 1.50, "output": 6.00},
            "computer-use-preview": {"input": 3.00, "output": 12.00},
            "gpt-image-1": {"input": 5.00, "output": 0.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "default": {"input": 1.00, "output": 2.00},
        }

        # Find the appropriate pricing for this model
        model_key = None
        for key in pricing:
            if key in self.model.lower():
                model_key = key
                break

        if not model_key:
            model_key = "default"

        model_pricing = pricing[model_key]

        # Calculate costs (convert from per 1M tokens to per token)
        input_cost = (self.prompt_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (self.completion_tokens / 1_000_000) * model_pricing["output"]

        total_cost = input_cost + output_cost

        # Apply batch discount (50% off for batch processing)
        if self.is_batched:
            total_cost *= 0.5

        return round(total_cost, 6)  # Round to 6 decimal places for precision


class LLMUsageStats(BaseModel):
    """LLM usage statistics model."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    average_response_time_ms: float = 0.0
    most_used_model: str | None = None
    date_range_start: str | None = None
    date_range_end: str | None = None
