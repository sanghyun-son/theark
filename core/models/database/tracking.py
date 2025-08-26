"""Database models for tracking external service usage."""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from core.constants import (
    BATCH_DISCOUNT_MULTIPLIER,
    COST_PRECISION,
    OPENAI_PRICING,
    TOKENS_PER_MILLION,
)


class LLMRequest(BaseModel):
    """LLM request tracking database entity model."""

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
    is_batched: bool = Field(
        default=False, description="Whether this was a batch request"
    )
    request_type: str = Field(
        default="chat", description="Type of request (chat, completion, embedding)"
    )
    custom_id: str | None = Field(
        default=None, description="Custom ID for tracking specific operations"
    )
    prompt_tokens: int | None = Field(default=None, description="Tokens in the prompt")
    completion_tokens: int | None = Field(
        default=None, description="Tokens in the completion"
    )
    total_tokens: int | None = Field(default=None, description="Total tokens used")
    response_time_ms: int | None = Field(
        default=None, description="Response time in milliseconds"
    )
    status: str = Field(
        default="pending", description="Request status (pending, success, error)"
    )
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    http_status_code: int | None = Field(default=None, description="HTTP status code")
    estimated_cost_usd: float | None = Field(
        default=None, description="Estimated cost in USD"
    )
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

    @classmethod
    def from_tuple(cls, row: tuple[Any, ...]) -> "LLMRequest":
        """Create LLMRequest from database tuple row."""
        metadata = None
        if row[16]:  # metadata column index
            metadata = json.loads(row[16])

        return cls(
            request_id=row[0],  # request_id
            timestamp=row[1],  # timestamp
            model=row[2],  # model
            provider=row[3],  # provider
            endpoint=row[4],  # endpoint
            is_batched=bool(row[5]),  # is_batched
            request_type=row[6],  # request_type
            custom_id=row[7],  # custom_id
            prompt_tokens=row[8],  # prompt_tokens
            completion_tokens=row[9],  # completion_tokens
            total_tokens=row[10],  # total_tokens
            response_time_ms=row[11],  # response_time_ms
            status=row[12],  # status
            error_message=row[13],  # error_message
            http_status_code=row[14],  # http_status_code
            estimated_cost_usd=row[15],  # estimated_cost_usd
            metadata=metadata,
        )

    def calculate_cost(self) -> float:
        """Calculate the estimated cost based on OpenAI's current pricing.

        Based on https://platform.openai.com/docs/pricing?latest-pricing=standard
        Only text tokens are considered. Batch processing is 50% of regular pricing.

        Returns:
            Estimated cost in USD
        """
        if not self.prompt_tokens or not self.completion_tokens:
            return 0.0

        # Find the appropriate pricing for this model
        model_key = None
        for key in OPENAI_PRICING:
            if key in self.model.lower():
                model_key = key
                break

        if not model_key:
            model_key = "default"

        model_pricing = OPENAI_PRICING[model_key]

        # Calculate costs (convert from per 1M tokens to per token)
        input_cost = (self.prompt_tokens / TOKENS_PER_MILLION) * model_pricing["input"]
        output_cost = (self.completion_tokens / TOKENS_PER_MILLION) * model_pricing[
            "output"
        ]

        total_cost = input_cost + output_cost

        # Apply batch discount
        if self.is_batched:
            total_cost *= BATCH_DISCOUNT_MULTIPLIER

        return round(total_cost, COST_PRECISION)


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
