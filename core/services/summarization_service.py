"""Paper summarization service for handling paper summarization logic."""

from sqlmodel import Session

from core import get_logger
from core.database.repository import LLMBatchRepository, SummaryRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.llm.response_parser import parse_tool_call_response
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
from core.models.rows import Paper, Summary
from core.types import PaperSummaryStatus

logger = get_logger(__name__)


class PaperSummarizationService:
    """Service for paper summarization operations."""

    def __init__(
        self,
        version: str = "0.1.0",
        default_interests: list[str] = ["Machine Learning"],
    ) -> None:
        """Initialize paper summarization service.

        Args:
            version: Application version for summary tracking
            default_interests: Default interests to use for summarization
        """
        self.version = version
        self.default_interests = default_interests

    def _create_summarization_messages(
        self,
        content: str,
        language: str,
        interests: list[str],
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
                    interests=", ".join(interests),
                    content=content,
                ),
            ),
        ]

    def _build_summarization_request(
        self,
        abstract: str,
        language: str,
        interests: list[str],
        model: str,
        use_tools: bool,
    ) -> ChatCompletionRequest:

        messages = self._create_summarization_messages(
            abstract,
            language,
            interests,
        )
        tools = None
        tool_choice = None
        if use_tools:
            tools = [self._create_paper_analysis_tool(language)]
            tool_choice = self._create_tool_choice()

        payload = ChatCompletionRequest(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        return payload

    def _parse_summarization_response(
        self,
        response: ChatCompletionResponse,
        language: str,
        interests: list[str],
        use_tools: bool = True,
    ) -> Summary:
        """Parse OpenAI chat completion response into Summary."""

        if not response.choices or not response.choices[0].message:
            raise ValueError("No response content received")

        message = response.choices[0].message

        # Handle tool responses with Pydantic validation
        structured_summary = None
        if message.tool_calls and use_tools:
            tool_call = message.tool_calls[0]
            if tool_call.function.name == "Structure":
                structured_summary = parse_tool_call_response(tool_call, PaperAnalysis)

        if structured_summary is None:
            raise ValueError("Failed to parse structured summary from tool response")

        return Summary(
            paper_id=None,
            version=self.version,
            overview=structured_summary.tldr,
            motivation=structured_summary.motivation,
            method=structured_summary.method,
            result=structured_summary.result,
            conclusion=structured_summary.conclusion,
            language=language,
            interests=", ".join(interests),
            relevance=structured_summary.relevance,
            model=response.model,
        )

    async def _summarize(
        self,
        content: str,
        llm_client: UnifiedOpenAIClient,
        language: str = "English",
        model: str | None = None,
        use_tools: bool | None = None,
    ) -> Summary | None:
        """Summarize a paper using the standard prompt structure.

        Args:
            content: Paper abstract content
            interest_section: User's interest section
            language: Language for the response
            model: Model to use (defaults to client model)
            use_tools: Whether to use tools (defaults to client setting)
            db_session: Database manager for tracking (optional)
            custom_id: Custom identifier for tracking (optional)

        Returns:
            Chat completion response
        """
        model = model or llm_client.model
        use_tools = use_tools if use_tools is not None else llm_client.use_tools

        payload = self._build_summarization_request(
            content,
            language,
            self.default_interests,
            model,
            use_tools,
        )
        request_data = payload.model_dump()
        response = await llm_client._client.chat.completions.create(**request_data)

        response_dict = response.model_dump()
        chat_response = ChatCompletionResponse.model_validate(response_dict)
        return self._parse_summarization_response(
            chat_response,
            language,
            self.default_interests,
            use_tools=use_tools,
        )

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
        db_session: Session,
    ) -> None:
        """Update LLM request tracking in database."""
        # This would integrate with the existing LLM tracking system
        # For now, just log the tracking info
        logger.debug(
            f"Tracking request {custom_id}: "
            f"status={status_code}, tokens={chat_response.usage}"
        )

    async def summarize_paper(
        self,
        paper: Paper,
        db_session: Session,
        llm_client: UnifiedOpenAIClient,
        force_resummarize: bool = False,
        language: str = "Korean",
    ) -> Summary | None:
        """Summarize a paper asynchronously."""

        # Check if summary already exists and force_resummarize is False
        if not force_resummarize and self._has_existing_summary(
            paper, db_session, language
        ):
            logger.warning(
                f"Summary already exists for paper {paper.arxiv_id} in {language}"
            )
            return None

        # Mark paper as processing to prevent batch manager from picking it up
        batch_repo = LLMBatchRepository(db_session)
        if paper.paper_id is not None:
            batch_repo.update_paper_summary_status(
                paper.paper_id, PaperSummaryStatus.PROCESSING
            )

        # Get summary using OpenAI client's built-in retry
        logger.info(f"[{paper.arxiv_id}] Summary requested in {language}")
        summary = await self._summarize(
            paper.abstract,
            llm_client,
            language=language,
        )
        logger.info(f"[{paper.arxiv_id}] Summarized in {language}")

        if summary is None:
            if paper.paper_id:
                batch_repo.update_paper_summary_status(
                    paper.paper_id, PaperSummaryStatus.ERROR
                )
            return None

        # Save summary and update status
        summary = self.save_summary(paper, summary, db_session)
        if paper.paper_id is not None:
            batch_repo.update_paper_summary_status(
                paper.paper_id, PaperSummaryStatus.DONE
            )

        return summary

    def _has_existing_summary(
        self, paper: Paper, db_session: Session, language: str
    ) -> bool:
        """Check if a summary already exists for the paper."""
        if not paper.paper_id:
            return False

        summary_repo = SummaryRepository(db_session)
        existing_summary = summary_repo.get_by_paper_id_and_language(
            paper.paper_id, language
        )
        return existing_summary is not None

    def save_summary(
        self,
        paper: Paper,
        summary: Summary,
        db_session: Session,
    ) -> Summary:
        """Save summary to database."""

        summary_repo = SummaryRepository(db_session)
        summary.paper_id = paper.paper_id
        logger.debug(f"{summary.model_dump()}")
        summary = summary_repo.create(summary)
        return summary

    async def get_summary(
        self, paper_id: int | None, db_session: Session, language: str = "Korean"
    ) -> Summary | None:
        """Get paper summary by language with fallback to English.

        Args:
            paper_id: Paper ID (can be None)
            db_session: Database session
            language: Preferred language (defaults to "Korean")

        Returns:
            Summary if found, None otherwise
        """
        if paper_id is None:
            logger.debug("Cannot get summary: paper_id is None")
            return None

        summary_repo = SummaryRepository(db_session)

        # Try to get summary in requested language
        summary = summary_repo.get_by_paper_id_and_language(paper_id, language)

        # If not found and language is not English, try English as fallback
        if summary is None and language != "English":
            logger.debug(
                f"Summary not found in {language} for paper {paper_id}, "
                f"trying English fallback"
            )
            summary = summary_repo.get_by_paper_id_and_language(paper_id, "English")

        if summary is None:
            logger.debug(f"No summary found for paper {paper_id} in any language")

        return summary
