"""Unified OpenAI client for both regular and batch requests using official OpenAI client."""

import asyncio
from pathlib import Path
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from core.database.interfaces import DatabaseManager
from core.log import get_logger
from core.models.external.openai import (
    BatchRequest,
    BatchResponse,
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIFunction,
    OpenAIFunctionParameter,
    OpenAIMessage,
    OpenAITool,
    OpenAIToolChoice,
    PaperAnalysis,
)

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
        error_data: dict | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_data = error_data


class UnifiedOpenAIClient:
    """Unified OpenAI client for both regular and batch requests using official client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com",
        timeout: float = 60.0,
        model: str = "gpt-4o-mini",
        use_tools: bool = True,
    ) -> None:
        """Initialize the unified OpenAI client.

        Args:
            api_key: OpenAI API key
            base_url: OpenAI API base URL
            timeout: Request timeout in seconds
            model: Default model to use
            use_tools: Whether to use tools/function calling by default
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._model = model
        self._use_tools = use_tools

        # Initialize official OpenAI client
        # Use the base URL as provided (tests already include /v1 if needed)
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
            timeout=timeout,
        )

        logger.info(f"Initialized {self.__class__.__name__} with {base_url=}, {model=}")

    @property
    def model(self) -> str:
        """Get the default model name."""
        return self._model

    @property
    def use_tools(self) -> bool:
        """Get whether this client uses tools by default."""
        return self._use_tools

    # Regular chat completion methods
    async def create_chat_completion(
        self,
        messages: list[OpenAIMessage],
        model: str | None = None,
        use_tools: bool | None = None,
        db_manager: DatabaseManager | None = None,
        custom_id: str | None = None,
    ) -> ChatCompletionResponse:
        """Create a chat completion request with robust error handling.

        Args:
            messages: List of messages for the conversation
            model: Model to use (defaults to client model)
            use_tools: Whether to use tools (defaults to client setting)
            db_manager: Database manager for tracking (optional)
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

        if use_tools:
            payload.tools = [self._create_paper_analysis_tool()]
            payload.tool_choice = self._create_tool_choice()

        # Log request details
        logger.debug(
            f"Creating chat completion with model={model}, use_tools={use_tools}"
        )
        logger.debug(f"Request payload:\n{payload.model_dump_json(indent=2)}")

        try:
            # Convert to dict for official client
            request_data = payload.model_dump()

            # Make request using official client (uses built-in retry)
            response = await self._client.chat.completions.create(**request_data)

            # Convert response to our model
            response_dict = response.model_dump()
            logger.debug(f"Response received: {response_dict}")

            chat_response = ChatCompletionResponse.model_validate(response_dict)

            # Update tracking if provided
            if db_manager and custom_id:
                await self._update_tracking(custom_id, 200, chat_response, db_manager)

            return chat_response

        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise OpenAIRequestError(f"Chat completion failed: {e}")

    async def summarize_paper(
        self,
        content: str,
        interest_section: str,
        language: str = "English",
        model: str | None = None,
        use_tools: bool | None = None,
        db_manager: DatabaseManager | None = None,
        custom_id: str | None = None,
    ) -> ChatCompletionResponse:
        """Summarize a paper using the standard prompt structure.

        Args:
            content: Paper abstract content
            interest_section: User's interest section
            language: Language for the response
            model: Model to use (defaults to client model)
            use_tools: Whether to use tools (defaults to client setting)
            db_manager: Database manager for tracking (optional)
            custom_id: Custom identifier for tracking (optional)

        Returns:
            Chat completion response
        """
        messages = self._create_summarization_messages(
            content, interest_section, language
        )
        return await self.create_chat_completion(
            messages, model, use_tools, db_manager, custom_id
        )

    # Batch processing methods
    async def create_batch_request(
        self,
        input_file_id: str,
        completion_window: str = "24h",
        endpoint: str = "/v1/chat/completions",
        metadata: dict[str, Any] | None = None,
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

        try:
            # Use the correct API structure for the official client
            batch = await self._client.batches.create(
                input_file_id=input_file_id,
                completion_window=completion_window,
                endpoint=endpoint,
                metadata=metadata or {},
            )

            logger.info(f"Created batch request: {batch.id}")

            # Convert to our model
            batch_dict = batch.model_dump()
            return BatchRequest.model_validate(batch_dict)

        except Exception as e:
            logger.error(f"Batch request creation failed: {e}")
            raise OpenAIRequestError(f"Batch request creation failed: {e}")

    async def get_batch_status(self, batch_id: str) -> BatchResponse:
        """Get the status of a batch request.

        Args:
            batch_id: ID of the batch request

        Returns:
            Batch status response
        """
        logger.debug(f"Getting batch status for {batch_id}")

        try:
            batch = await self._client.batches.retrieve(batch_id=batch_id)

            logger.debug(f"Batch {batch_id} status: {batch.status}")

            # Convert to our model
            batch_dict = batch.model_dump()
            return BatchResponse.model_validate(batch_dict)

        except Exception as e:
            logger.error(f"Failed to get batch status for {batch_id}: {e}")
            raise OpenAIRequestError(f"Failed to get batch status: {e}")

    async def cancel_batch_request(self, batch_id: str) -> BatchResponse:
        """Cancel a batch request.

        Args:
            batch_id: ID of the batch request to cancel

        Returns:
            Batch response with updated status
        """
        logger.debug(f"Cancelling batch request {batch_id}")

        try:
            batch = await self._client.batches.cancel(batch_id=batch_id)

            logger.info(f"Cancelled batch request: {batch_id}")

            # Convert to our model
            batch_dict = batch.model_dump()
            return BatchResponse.model_validate(batch_dict)

        except Exception as e:
            logger.error(f"Failed to cancel batch {batch_id}: {e}")
            raise OpenAIRequestError(f"Failed to cancel batch: {e}")

    async def list_batch_requests(
        self, limit: int = 10, after: str | None = None
    ) -> list[BatchResponse]:
        """List batch requests.

        Args:
            limit: Maximum number of requests to return
            after: Cursor for pagination

        Returns:
            List of batch responses
        """
        logger.debug(f"Listing batch requests with limit={limit}")

        try:
            params = {"limit": limit}
            if after:
                params["after"] = after

            batches = await self._client.batches.list(**params)

            # Convert to our models
            batch_responses = []
            for batch in batches.data:
                batch_dict = batch.model_dump()
                batch_responses.append(BatchResponse.model_validate(batch_dict))

            logger.debug(f"Retrieved {len(batch_responses)} batch requests")
            return batch_responses

        except Exception as e:
            logger.error(f"Failed to list batch requests: {e}")
            raise OpenAIRequestError(f"Failed to list batch requests: {e}")

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

                # Stop monitoring if batch is in a final state
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

    # File upload methods
    async def upload_file(self, file_path: str | Path, purpose: str = "batch") -> str:
        """Upload a file to OpenAI.

        Args:
            file_path: Path to the file to upload (string or Path object)
            purpose: Purpose of the file upload

        Returns:
            File ID
        """
        file_path = Path(file_path)
        logger.debug(f"Uploading file {file_path} with purpose={purpose}")

        try:
            # Check if file exists before attempting upload
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(file_path, "rb") as f:
                file_obj = await self._client.files.create(file=f, purpose=purpose)

            file_id = str(file_obj.id)
            logger.info(f"Uploaded file: {file_id}")
            return file_id

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"File upload failed for {file_path}: {e}")
            raise OpenAIRequestError(f"File upload failed: {e}")

    async def upload_data(
        self, data: str, filename: str, purpose: str = "batch"
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

        try:
            # Convert string data to bytes
            data_bytes = data.encode("utf-8")

            file_obj = await self._client.files.create(
                file=(filename, data_bytes, "application/json"),
                purpose=purpose,
            )

            file_id = str(file_obj.id)
            logger.info(f"Uploaded data as file: {file_id}")
            return file_id

        except Exception as e:
            logger.error(f"Data upload failed for {filename}: {e}")
            raise OpenAIRequestError(f"Data upload failed: {e}")

    async def download_file(self, file_id: str, output_path: str | Path) -> None:
        """Download a file from OpenAI.

        Args:
            file_id: ID of the file to download
            output_path: Path where to save the file (string or Path object)
        """
        output_path = Path(output_path)
        logger.debug(f"Downloading file {file_id} to {output_path}")

        try:
            content = await self._client.files.content(file_id=file_id)

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(content.read())

            logger.info(f"Downloaded file {file_id} to {output_path}")

        except Exception as e:
            logger.error(f"File download failed for {file_id}: {e}")
            raise OpenAIRequestError(f"File download failed: {e}")

    # Helper methods
    def _create_summarization_messages(
        self, content: str, interest_section: str, language: str
    ) -> list[OpenAIMessage]:
        """Create messages for paper summarization."""
        from core.llm.prompts import SYSTEM_PROMPT, USER_PROMPT

        return [
            OpenAIMessage(
                role="system",
                content=SYSTEM_PROMPT.format(language=language),
            ),
            OpenAIMessage(
                role="user",
                content=USER_PROMPT.format(
                    language=language,
                    interest_section=interest_section,
                    content=content,
                ),
            ),
        ]

    def _create_paper_analysis_tool(self) -> OpenAITool:
        """Create the paper analysis function calling tool."""
        function_parameters = OpenAIFunctionParameter(
            type="object",
            description="Paper analysis parameters",
            properties=PaperAnalysis.create_paper_analysis_schema(),
            required=PaperAnalysis.get_required_fields(),
        )

        function = OpenAIFunction(
            name="Structure",
            description="Analyze paper abstract and extract key information",
            parameters=function_parameters,
        )

        return OpenAITool(function=function)

    def _create_tool_choice(self) -> OpenAIToolChoice:
        """Create the tool choice configuration."""
        return OpenAIToolChoice(function={"name": "Structure"})

    async def _update_tracking(
        self,
        custom_id: str,
        status_code: int,
        chat_response: ChatCompletionResponse,
        db_manager: DatabaseManager,
    ) -> None:
        """Update LLM request tracking in database."""
        # This would integrate with the existing LLM tracking system
        # For now, just log the tracking info
        logger.debug(
            f"Tracking request {custom_id}: "
            f"status={status_code}, tokens={chat_response.usage}"
        )
