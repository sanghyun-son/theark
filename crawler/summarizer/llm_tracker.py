"""LLM request tracking wrapper."""

import time
from datetime import datetime
from typing import Any, Dict

from core import get_logger
from crawler.database import LLMRequest

logger = get_logger(__name__)


class LLMTracker:
    """Wrapper for tracking LLM API requests."""

    def __init__(self, custom_id: str | None = None, db_manager: Any = None):
        """Initialize LLM tracker.

        Args:
            custom_id: Custom ID for tracking related requests
            db_manager: LLM database manager instance (required)
        """
        self.custom_id = custom_id
        if db_manager is None:
            raise ValueError("db_manager is required for LLMTracker")
        self.db_manager = db_manager

    def start_request(
        self,
        model: str,
        provider: str = "openai",
        endpoint: str = "/v1/chat/completions",
        is_batched: bool = False,
        request_type: str = "chat",
        metadata: Dict[str, Any] | None = None,
    ) -> int:
        """Start tracking a new LLM request.

        Args:
            model: Model name (e.g., "gpt-4o-mini")
            provider: Provider name (e.g., "openai")
            endpoint: API endpoint
            is_batched: Whether this is a batch request
            request_type: Type of request (chat, completion, etc.)
            metadata: Additional metadata

        Returns:
            Request ID for tracking
        """
        request = LLMRequest(
            timestamp=datetime.now().isoformat(),
            model=model,
            provider=provider,
            endpoint=endpoint,
            is_batched=is_batched,
            request_type=request_type,
            custom_id=self.custom_id,
            status="pending",
            metadata=metadata,
        )

        request_id = self.db_manager.repository.create(request)
        logger.debug(f"Started tracking LLM request {request_id}")
        return int(request_id)

    def complete_request(
        self,
        request_id: int,
        success: bool,
        response_time_ms: int,
        tokens: Dict[str, int] | None = None,
        error_message: str | None = None,
        http_status_code: int | None = None,
        estimated_cost_usd: float | None = None,
    ) -> None:
        """Complete tracking of an LLM request.

        Args:
            request_id: Request ID from start_request
            success: Whether the request succeeded
            response_time_ms: Response time in milliseconds
            tokens: Token usage dict (prompt_tokens, completion_tokens, total_tokens)
            error_message: Error message if failed
            http_status_code: HTTP status code
            estimated_cost_usd: Estimated cost in USD
        """
        status = "success" if success else "error"

        self.db_manager.repository.update_status(
            request_id=request_id,
            status=status,
            response_time_ms=response_time_ms,
            tokens=tokens,
            error_message=error_message,
            http_status_code=http_status_code,
        )

        # Update cost if provided
        if estimated_cost_usd is not None:
            # Would need to add a separate method for this, but for now we can
            # include it in metadata
            pass

        logger.debug(
            f"Completed tracking LLM request {request_id} with status {status}"
        )


class LLMRequestContext:
    """Context manager for tracking LLM requests."""

    def __init__(
        self,
        model: str,
        custom_id: str | None = None,
        provider: str = "openai",
        endpoint: str = "/v1/chat/completions",
        is_batched: bool = False,
        request_type: str = "chat",
        metadata: Dict[str, Any] | None = None,
        db_manager: Any = None,
    ):
        """Initialize LLM request context.

        Args:
            model: Model name
            custom_id: Custom ID for tracking
            provider: Provider name
            endpoint: API endpoint
            is_batched: Whether this is a batch request
            request_type: Type of request
            metadata: Additional metadata
            db_manager: Optional LLM database manager instance
        """
        self.tracker = LLMTracker(custom_id, db_manager)
        self.model = model
        self.provider = provider
        self.endpoint = endpoint
        self.is_batched = is_batched
        self.request_type = request_type
        self.metadata = metadata
        self.request_id: int | None = None
        self.start_time: float | None = None
        self.db_manager = db_manager

    def __enter__(self) -> "LLMRequestContext":
        """Enter context manager."""
        self.start_time = time.time()
        self.request_id = self.tracker.start_request(
            model=self.model,
            provider=self.provider,
            endpoint=self.endpoint,
            is_batched=self.is_batched,
            request_type=self.request_type,
            metadata=self.metadata,
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit context manager."""
        if self.request_id is None or self.start_time is None:
            return

        end_time = time.time()
        response_time_ms = int((end_time - self.start_time) * 1000)

        success = exc_type is None
        error_message = str(exc_val) if exc_val else None

        self.tracker.complete_request(
            request_id=self.request_id,
            success=success,
            response_time_ms=response_time_ms,
            error_message=error_message,
        )

    def update_tokens(self, tokens: Dict[str, int]) -> None:
        """Update token usage for the request.

        Args:
            tokens: Token usage dict (prompt_tokens, completion_tokens, total_tokens)
        """
        if self.request_id is not None and self.db_manager:
            # Calculate cost based on tokens
            estimated_cost = None
            if "prompt_tokens" in tokens and "completion_tokens" in tokens:
                # Create a temporary request object to calculate cost
                temp_request = LLMRequest(
                    model=self.model,
                    is_batched=self.is_batched,
                    prompt_tokens=tokens["prompt_tokens"],
                    completion_tokens=tokens["completion_tokens"],
                )
                estimated_cost = temp_request.calculate_cost()

            self.db_manager.repository.update_status(
                request_id=self.request_id,
                status="success",  # Keep current status
                tokens=tokens,
                estimated_cost_usd=estimated_cost,
            )

    def update_http_status(self, status_code: int) -> None:
        """Update HTTP status code for the request.

        Args:
            status_code: HTTP status code
        """
        if self.request_id is not None and self.db_manager:
            self.db_manager.repository.update_status(
                request_id=self.request_id,
                status="success" if 200 <= status_code < 300 else "error",
                http_status_code=status_code,
            )
