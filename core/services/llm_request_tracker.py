"""Async context manager for tracking LLM requests."""

import time
from types import TracebackType
from typing import Any

from sqlmodel import Session

from core.constants import (
    COST_PRECISION,
    OPENAI_PRICING,
    TOKENS_PER_MILLION,
)
from core.database.repository import LLMRequestRepository
from core.log import get_logger
from core.models.rows import LLMRequest
from core.utils import get_current_timestamp

logger = get_logger(__name__)


class LLMRequestTracker:
    """Universal async context manager for tracking any LLM request."""

    def __init__(
        self,
        db_session: Session,
        provider: str = "openai",
        endpoint: str = "/v1/chat/completions",
    ):
        """Initialize LLM request tracker.

        Args:
            db_session: Database session (required)
            model: LLM model name
            provider: LLM provider (default: openai)
            endpoint: API endpoint called
            custom_id: Custom identifier for tracking
            request_type: Type of request (chat, completion, embedding, etc.)
            metadata: Additional metadata for the request
        """
        self.db_session = db_session
        self.provider = provider
        self.endpoint = endpoint
        self.request_record: LLMRequest | None = None
        self.start_time = time.time()
        self.response: Any = None

    async def __aenter__(self) -> "LLMRequestTracker":
        """Enter the context and log request start."""
        self.request_record = await self._log_request_start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context and automatically log request completion."""
        await self._auto_log_completion(exc_type, exc_val)
        if exc_type is not None:
            logger.error(f"LLM request failed: {exc_val}")

    async def _log_request_start(self) -> LLMRequest:
        """Log the start of an LLM request."""
        llm_request_repo = LLMRequestRepository(self.db_session)

        request = LLMRequest(
            timestamp=get_current_timestamp(),
            model="...",
            provider=self.provider,
            endpoint=self.endpoint,
            status="pending",
        )

        return llm_request_repo.create(request)

    async def _auto_log_completion(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
    ) -> None:
        """Automatically log completion based on response or exception."""
        if not self.request_record:
            return

        llm_request_repo = LLMRequestRepository(self.db_session)
        response_time_ms = int((time.time() - self.start_time) * 1000)

        if exc_type is not None:
            # 에러 케이스
            self.request_record.status = "error"
            self.request_record.error_message = str(exc_val)
            self.request_record.response_time_ms = response_time_ms
            self.request_record.http_status_code = 500
        elif self.response and hasattr(self.response, "usage") and self.response.usage:
            # 성공 케이스 - OpenAI ChatCompletion 응답에서 자동으로 정보 추출
            self.request_record.status = "success"
            self.request_record.prompt_tokens = self.response.usage.prompt_tokens
            self.request_record.completion_tokens = (
                self.response.usage.completion_tokens
            )
            self.request_record.total_tokens = self.response.usage.total_tokens
            self.request_record.response_time_ms = response_time_ms
            self.request_record.http_status_code = 200

            # 비용 자동 계산
            cost = self._calculate_cost(
                self.request_record.model,
                self.response.usage.prompt_tokens,
                self.response.usage.completion_tokens,
            )
            self.request_record.estimated_cost_usd = cost
        elif self.response and hasattr(self.response, "id"):
            # 성공 케이스 - OpenAI Batch/File 등 다른 응답에서
            self.request_record.status = "success"
            self.request_record.response_time_ms = response_time_ms
            self.request_record.http_status_code = 200

            # Batch response는 토큰 정보가 없으므로 비용 계산 불가
            self.request_record.estimated_cost_usd = None
        else:
            # 응답이 없거나 예상과 다른 경우
            self.request_record.status = "unknown"
            self.request_record.response_time_ms = response_time_ms

        llm_request_repo.update(self.request_record)

    def set_response(self, response: Any) -> None:
        """Set the LLM response for automatic logging.

        Args:
            response: LLM response object (e.g., OpenAI ChatCompletion)
        """
        self.response = response

    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate estimated cost using existing constants."""

        model_pricing = OPENAI_PRICING.get(model, OPENAI_PRICING["default"])

        input_cost = (prompt_tokens / TOKENS_PER_MILLION) * model_pricing["input"]
        output_cost = (completion_tokens / TOKENS_PER_MILLION) * model_pricing["output"]

        total_cost = input_cost + output_cost
        return round(total_cost, COST_PRECISION)
