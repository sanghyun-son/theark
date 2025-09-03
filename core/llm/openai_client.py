"""Unified OpenAI client for both regular and batch requests using official client."""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from sqlmodel import Session

from core.log import get_logger
from core.models.external.openai import (
    BatchEndpoint,
    BatchRequest,
    BatchResponse,
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionWindow,
    FilePurpose,
    OpenAIMessage,
)
from core.services.llm_request_tracker import LLMRequestTracker

logger = get_logger(__name__)


class OpenAIError(Exception):
    """Base exception for OpenAI client errors."""

    pass


class OpenAIRequestError(OpenAIError):
    """Exception for OpenAI API request errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_data: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_data = error_data


class UnifiedOpenAIClient:
    """Unified OpenAI client for both regular and batch requests."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com",
        timeout: float = 60.0,
        model: str = "gpt-4o-mini",
        use_tools: bool = True,
        max_retries: int = 3,
    ) -> None:
        """Initialize the unified OpenAI client.

        Args:
            api_key: OpenAI API key
            base_url: OpenAI API base URL
            timeout: Request timeout in seconds
            model: Default model to use
            use_tools: Whether to use tools/function calling by default
            max_retries: Maximum number of retries for failed requests
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._model = model
        self._use_tools = use_tools

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"with {base_url=}, {model=}, {max_retries=}"
        )

    @property
    def model(self) -> str:
        """Get the default model name."""
        return self._model

    @property
    def use_tools(self) -> bool:
        """Get whether this client uses tools by default."""
        return self._use_tools

    async def create_chat_completion(
        self,
        messages: list[OpenAIMessage],
        db_session: Session,
        model: str | None = None,
        use_tools: bool | None = None,
    ) -> ChatCompletionResponse:
        """Create a chat completion request with robust error handling.

        Args:
            messages: List of messages for the conversation
            model: Model to use (defaults to client model)
            use_tools: Whether to use tools (defaults to client setting)
            db_session: Database manager for tracking (optional)
            custom_id: Custom identifier for tracking (optional)

        Returns:
            Chat completion response

        Raises:
            OpenAIRequestError: If the request fails
        """
        model = model or self._model
        use_tools = use_tools if use_tools is not None else self._use_tools

        # Build request payload
        payload = ChatCompletionRequest(
            model=model,
            messages=messages,
        )

        logger.debug(f"/v1/chat/completions model={model}")
        logger.debug(f"Request payload:\n{payload.model_dump_json(indent=2)}")
        request_data = payload.model_dump()

        async with LLMRequestTracker(
            db_session=db_session,
            endpoint="/v1/chat/completions",
        ) as tracker:

            response = await self._client.chat.completions.create(**request_data)
            tracker.set_response(response)

        response_dict = response.model_dump()
        logger.debug(f"Response received: {response_dict}")

        chat_response = ChatCompletionResponse.model_validate(response_dict)

        # Note: Tracking is now handled by PaperSummarizationService

        return chat_response

    # Batch processing methods
    async def create_batch_request(
        self,
        input_file_id: str,
        completion_window: CompletionWindow = "24h",
        endpoint: BatchEndpoint = "/v1/chat/completions",
    ) -> BatchRequest:
        """Create a new batch request using official client.

        Args:
            input_file_id: ID of the input file uploaded to OpenAI
            completion_window: Time window for completion (e.g., "24h")
            endpoint: API endpoint to use for requests
            metadata: Optional metadata for the batch

        Returns:
            Batch request response
        """
        logger.debug(f"Creating batch request with file_id={input_file_id}")
        batch = await self._client.batches.create(
            input_file_id=input_file_id,
            completion_window=completion_window,
            endpoint=endpoint,
        )
        logger.info(f"Created batch request: {batch.id}")

        batch_dict = batch.model_dump()
        return BatchRequest.model_validate(batch_dict)

    async def get_batch_status(self, batch_id: str) -> BatchResponse:
        """Get the status of a batch request.

        Args:
            batch_id: ID of the batch request
            db_session: Database session for tracking (optional)
            custom_id: Custom identifier for tracking (optional)

        Returns:
            Batch status response
        """
        logger.debug(f"Getting batch status for {batch_id}")
        batch = await self._client.batches.retrieve(batch_id=batch_id)
        logger.debug(f"Batch {batch_id} status: {batch.status}")

        batch_dict = batch.model_dump()
        return BatchResponse.model_validate(batch_dict)

    async def cancel_batch_request(self, batch_id: str) -> BatchResponse:
        """Cancel a batch request.

        Args:
            batch_id: ID of the batch request to cancel
            db_session: Database session for tracking (optional)
            custom_id: Custom identifier for tracking (optional)

        Returns:
            Batch response with updated status
        """
        logger.debug(f"Cancelling batch request {batch_id}")
        batch = await self._client.batches.cancel(batch_id=batch_id)
        logger.info(f"Cancelled batch request: {batch_id}")

        batch_dict = batch.model_dump()
        return BatchResponse.model_validate(batch_dict)

    async def list_batch_requests(
        self,
        limit: int = 10,
        after: str | None = None,
    ) -> list[BatchResponse]:
        """List batch requests.

        Args:
            limit: Maximum number of requests to return
            after: Cursor for pagination

        Returns:
            List of batch responses
        """
        logger.debug(f"Listing batch requests with limit={limit}")

        if after:
            batches = await self._client.batches.list(limit=limit, after=after)
        else:
            batches = await self._client.batches.list(limit=limit)

        # Convert to our models
        batch_responses = []
        for batch in batches.data:
            batch_dict = batch.model_dump()
            batch_responses.append(BatchResponse.model_validate(batch_dict))

        logger.debug(f"Retrieved {len(batch_responses)} batch requests")
        return batch_responses

    async def monitor_batch_progress(
        self, batch_id: str, check_interval: float = 10.0
    ) -> AsyncGenerator[BatchResponse, None]:
        """Monitor batch request progress.

        Args:
            batch_id: ID of the batch request to monitor
            check_interval: Interval between status checks in seconds

        Yields:
            Batch status updates
        """
        logger.info(f"Starting batch progress monitoring for {batch_id}")

        while True:
            try:
                batch_status = await self.get_batch_status(batch_id)
                yield batch_status

                if batch_status.status in [
                    "completed",
                    "failed",
                    "expired",
                    "cancelled",
                ]:
                    logger.info(
                        f"Batch {batch_id} reached final state: {batch_status.status}"
                    )
                    break

                await asyncio.sleep(check_interval)

            except OpenAIRequestError as e:
                logger.error(f"Error monitoring batch {batch_id}: {e}")
                raise

    async def upload_file(
        self, file_path: str | Path, purpose: FilePurpose = "batch"
    ) -> str:
        """Upload a file to OpenAI.

        Args:
            file_path: Path to the file to upload (string or Path object)
            purpose: Purpose of the file upload

        Returns:
            File ID
        """
        file_path = Path(file_path)
        logger.debug(f"Uploading file {file_path} with purpose={purpose}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            file_obj = await self._client.files.create(file=f, purpose=purpose)

        file_id = str(file_obj.id)
        logger.info(f"Uploaded file: {file_id}")
        return file_id

    async def upload_data(
        self, data: str, filename: str, purpose: FilePurpose = "batch"
    ) -> str:
        """Upload data directly from memory to OpenAI.

        Args:
            data: Data content as string
            filename: Name for the file
            purpose: Purpose of the file upload

        Returns:
            File ID
        """
        logger.debug(f"Uploading data as file {filename} with purpose={purpose}")

        data_bytes = data.encode("utf-8")

        file_obj = await self._client.files.create(
            file=(filename, data_bytes, "application/json"),
            purpose=purpose,
        )

        file_id = str(file_obj.id)
        logger.info(f"Uploaded data as file: {file_id}")
        return file_id

    async def download_file(self, file_id: str, output_path: str | Path) -> None:
        """Download a file from OpenAI.

        Args:
            file_id: ID of the file to download
            output_path: Path where to save the file (string or Path object)
        """
        output_path = Path(output_path)
        logger.debug(f"Downloading file {file_id} to {output_path}")

        content = await self._client.files.content(file_id=file_id)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(content.read())

        logger.info(f"Downloaded file {file_id} to {output_path}")
