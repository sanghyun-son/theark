"""Summary generation application using LLM clients."""

from core.database.interfaces import DatabaseManager
from core.llm.openai_client import UnifiedOpenAIClient
from core.log import get_logger
from core.models.external.openai import (
    ChatCompletionResponse,
    OpenAIFunction,
    OpenAIFunctionParameter,
    OpenAIMessage,
    OpenAITool,
    OpenAIToolChoice,
    PaperAnalysis,
)

logger = get_logger(__name__)


class SummaryGenerator:
    """Generator for paper summaries using LLM clients."""

    async def summarize_paper(
        self,
        llm_client: UnifiedOpenAIClient,
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

        # Create tools if requested
        tools = None
        tool_choice = None
        if use_tools if use_tools is not None else llm_client.use_tools:
            tools = [self._create_paper_analysis_tool(language)]
            tool_choice = self._create_tool_choice()

        # Create the request payload manually to include tools
        from core.models.external.openai import ChatCompletionRequest

        payload = ChatCompletionRequest(
            model=model or llm_client.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )

        # Convert to dict for official client
        request_data = payload.model_dump()

        # Make request using official client
        response = await llm_client._client.chat.completions.create(**request_data)

        # Convert response to our model
        response_dict = response.model_dump()
        chat_response = ChatCompletionResponse.model_validate(response_dict)

        # Update tracking if provided
        if db_manager and custom_id:
            await self._update_tracking(custom_id, 200, chat_response, db_manager)

        return chat_response

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

    def _create_paper_analysis_tool(self, language: str) -> OpenAITool:
        """Create the paper analysis function calling tool."""
        function_parameters = OpenAIFunctionParameter(
            type="object",
            description="Paper analysis parameters",
            properties=PaperAnalysis.create_paper_analysis_schema(language),
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
