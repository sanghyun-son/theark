"""OpenAI-based abstract summarizer."""

from typing import Any

import httpx

from core.log import get_logger
from core.models.external.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIFunction,
    OpenAIFunctionParameter,
    OpenAIMessage,
    OpenAITool,
    OpenAIToolChoice,
    PaperAnalysis,
)
from crawler.database.llm_sqlite_manager import LLMSQLiteManager

from .client import SummaryClient
from .llm_tracker import LLMRequestContext
from .prompt import SYSTEM_PROMPT, USER_PROMPT
from .summarizer import (
    SummaryRequest,
    SummaryResponse,
)

logger = get_logger(__name__)


class OpenAISummarizer(SummaryClient):
    """OpenAI-based implementation of abstract summarizer."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 60.0,
        model: str = "gpt-4o-mini",
        use_tools: bool = True,
    ):
        """Initialize the OpenAI summarizer."""
        from core.config import settings

        self.api_key = api_key
        self.base_url = base_url or settings.llm_api_base_url
        self.timeout = timeout
        self._model = model
        self._use_tools = use_tools
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    @property
    def model(self) -> str:
        """Get the model name used by this client."""
        return self._model

    @property
    def use_tools(self) -> bool:
        """Get whether this client uses tools/function calling."""
        return self._use_tools

    async def summarize(
        self, request: SummaryRequest, db_manager: LLMSQLiteManager
    ) -> SummaryResponse:
        """Summarize the given abstract using OpenAI API."""
        llm_context = LLMRequestContext(
            model=request.model,
            custom_id=request.custom_id,
            provider="openai",
            endpoint="/v1/chat/completions",
            is_batched=False,
            request_type="chat",
            metadata=self._create_request_metadata(request),
        )
        llm_context.db_manager = db_manager

        with llm_context as context:
            # Build and send request
            payload = self._build_request_payload(request)
            logger.debug(
                f"OpenAI Request to {self.base_url}:\n"
                f"{payload.model_dump_json(indent=2)}"
            )
            response = await self._make_api_request(payload)

            # Update tracking with response data
            context.update_http_status(response.status_code, db_manager)

            if response.status_code != 200:
                raise Exception(
                    f"OpenAI API error: {response.status_code} - {response.text}"
                )

            # Parse response
            chat_response = ChatCompletionResponse(**response.json())
            logger.debug(f"OpenAI Response:\n{chat_response.model_dump_json(indent=2)}")
            self._update_token_tracking(context, chat_response, db_manager)

            return self._parse_response(request, chat_response)

    def _create_request_metadata(self, request: SummaryRequest) -> dict[str, Any]:
        """Create metadata for the LLM request tracking."""
        return {
            "use_tools": request.use_tools,
            "language": request.language,
            "content_length": len(request.content),
        }

    def _build_request_payload(self, request: SummaryRequest) -> ChatCompletionRequest:
        """Build the OpenAI API request payload."""
        messages = self._create_messages(request)
        payload = ChatCompletionRequest(model=request.model, messages=messages)

        if request.use_tools:
            payload.tools = [self._create_tool()]
            payload.tool_choice = self._create_tool_choice()

        return payload

    def _create_messages(self, request: SummaryRequest) -> list[OpenAIMessage]:
        """Create the messages for the OpenAI API request."""
        return [
            OpenAIMessage(
                role="system",
                content=SYSTEM_PROMPT.format(language=request.language),
            ),
            OpenAIMessage(
                role="user",
                content=USER_PROMPT.format(
                    language=request.language,
                    interest_section=request.interest_section,
                    content=request.content,
                ),
            ),
        ]

    def _create_tool(self) -> OpenAITool:
        """Create the function calling tool."""
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

    async def _make_api_request(self, payload: ChatCompletionRequest) -> httpx.Response:
        """Make the API request to OpenAI."""
        return await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload.model_dump(),
        )

    def _update_token_tracking(
        self,
        llm_context: LLMRequestContext,
        chat_response: ChatCompletionResponse,
        db_manager: LLMSQLiteManager,
    ) -> None:
        """Update token usage tracking."""
        if chat_response.usage:
            llm_context.update_tokens(
                {
                    "prompt_tokens": chat_response.usage.prompt_tokens,
                    "completion_tokens": chat_response.usage.completion_tokens,
                    "total_tokens": chat_response.usage.total_tokens,
                },
                db_manager,
            )

    def _parse_response(
        self, request: SummaryRequest, chat_response: ChatCompletionResponse
    ) -> SummaryResponse:
        """Parse the OpenAI API response."""
        choice = chat_response.choices[0]
        message = choice.message
        metadata = self._create_response_metadata(request, chat_response, choice)

        if request.use_tools and message.tool_calls:
            return self._parse_structured_response(request, message, metadata)
        else:
            return self._parse_text_response(request, message, metadata)

    def _create_response_metadata(
        self,
        request: SummaryRequest,
        chat_response: ChatCompletionResponse,
        choice: Any,
    ) -> dict[str, Any]:
        """Create metadata for the response."""
        return {
            "model": request.model,
            "usage": chat_response.usage.model_dump() if chat_response.usage else None,
            "finish_reason": choice.finish_reason,
        }

    def _parse_structured_response(
        self, request: SummaryRequest, message: OpenAIMessage, metadata: dict[str, Any]
    ) -> SummaryResponse:
        """Parse structured response with function calling."""
        if not message.tool_calls:
            raise ValueError("Expected tool calls but none found")

        tool_call = message.tool_calls[0]
        analysis_args = PaperAnalysis.from_json_string(tool_call.function.arguments)

        return SummaryResponse(
            custom_id=request.custom_id,
            structured_summary=analysis_args,
            original_length=len(request.content),
            summary_length=len(analysis_args.tldr),
            metadata=metadata,
        )

    def _parse_text_response(
        self, request: SummaryRequest, message: OpenAIMessage, metadata: dict[str, Any]
    ) -> SummaryResponse:
        """Parse regular text response."""
        content = message.content or ""

        return SummaryResponse(
            custom_id=request.custom_id,
            summary=content,
            original_length=len(request.content),
            summary_length=len(content),
            metadata=metadata,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
