"""Unified batch request builder using the same prompt structure as summarizer."""

from typing import Any

from core.log import get_logger
from core.models.batch import BatchRequestEntry, BatchRequestPayload
from core.models.external.openai import (
    ChatCompletionRequest,
    OpenAIFunction,
    OpenAIFunctionParameter,
    OpenAIMessage,
    OpenAITool,
    OpenAIToolChoice,
    PaperAnalysis,
)

logger = get_logger(__name__)


class BatchBuilderError(Exception):
    """Base exception for batch builder errors."""

    pass


class UnifiedBatchBuilder:
    """Unified batch request builder using the same prompt structure."""

    @staticmethod
    def create_paper_summarization_batch(
        papers: list[dict[str, Any]],
        interest_section: str = "",
        language: str = "English",
        model: str = "gpt-4o-mini",
        use_tools: bool = True,  # Batch API supports tool calling
    ) -> BatchRequestPayload:
        """Create a batch request for paper summarization with robust error handling.

        Args:
            papers: List of papers with 'paper_id', 'title', 'abstract', 'arxiv_id' keys
            interest_section: User's interest section for relevance assessment
            language: Language for the response
            model: Model to use for summarization
            use_tools: Whether to use function calling tools

        Returns:
            Batch request payload ready for upload

        Raises:
            BatchBuilderError: If batch creation fails
        """
        if not papers:
            logger.warning("No papers provided for batch creation")
            return BatchRequestPayload(entries=[])

        logger.debug(
            f"Creating batch for {len(papers)} papers with "
            f"model={model}, use_tools={use_tools}"
        )

        try:
            entries = []

            for i, paper in enumerate(papers):
                try:
                    entry = UnifiedBatchBuilder._create_batch_entry(
                        paper, interest_section, language, model, use_tools
                    )
                    entries.append(entry)
                    logger.debug(
                        f"Created batch entry {i+1}/{len(papers)} for "
                        f"paper {paper.get('paper_id', 'unknown')}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to create batch entry for "
                        f"paper {paper.get('paper_id', 'unknown')}: {e}"
                    )
                    # Continue with other papers instead of failing completely
                    continue

            if not entries:
                raise BatchBuilderError("No valid batch entries could be created")

            logger.info(f"Successfully created batch with {len(entries)} entries")
            return BatchRequestPayload(entries=entries)

        except Exception as e:
            logger.error(f"Batch creation failed: {e}")
            raise BatchBuilderError(f"Failed to create batch: {e}")

    @staticmethod
    def _create_batch_entry(
        paper: dict[str, Any],
        interest_section: str,
        language: str,
        model: str,
        use_tools: bool,
    ) -> BatchRequestEntry:
        """Create a single batch entry for a paper.

        Args:
            paper: Paper data dictionary
            interest_section: User's interest section
            language: Language for response
            model: Model to use
            use_tools: Whether to use tools

        Returns:
            Batch request entry

        Raises:
            BatchBuilderError: If entry creation fails
        """
        # Validate required paper fields
        required_fields = ["paper_id", "abstract"]
        missing_fields = [field for field in required_fields if not paper.get(field)]
        if missing_fields:
            raise BatchBuilderError(f"Missing required fields: {missing_fields}")

        # Create messages using the standard prompt structure
        messages = UnifiedBatchBuilder._create_summarization_messages(
            paper["abstract"],
            interest_section,
            language,
        )

        # Build the request payload
        payload = ChatCompletionRequest(model=model, messages=messages)

        # Add tools if requested
        if use_tools:
            payload.tools = [UnifiedBatchBuilder._create_paper_analysis_tool()]
            payload.tool_choice = UnifiedBatchBuilder._create_tool_choice()

        # Convert to dict for batch entry
        body = payload.model_dump()

        # Create batch entry
        entry = BatchRequestEntry(
            custom_id=str(paper["paper_id"]),
            method="POST",
            url="/v1/chat/completions",
            body=body,
        )

        return entry

    @staticmethod
    def _create_summarization_messages(
        content: str,
        interest_section: str,
        language: str,
    ) -> list[OpenAIMessage]:
        """Create messages for paper summarization using the standard prompt structure.

        Args:
            content: The content to summarize
            interest_section: User's interest section for relevance assessment
            language: Language for the response

        Returns:
            List of OpenAIMessages

        Raises:
            BatchBuilderError: If the content is empty or invalid
        """
        if not content or not content.strip():
            raise BatchBuilderError("Content cannot be empty")

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

    @staticmethod
    def _create_paper_analysis_tool() -> OpenAITool:
        """Create the paper analysis function calling tool.

        Returns:
            OpenAITool for paper analysis

        Raises:
            BatchBuilderError: If tool creation fails
        """
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

    @staticmethod
    def _create_tool_choice() -> OpenAIToolChoice:
        """Create the tool choice configuration.

        Returns:
            OpenAIToolChoice configuration

        Raises:
            BatchBuilderError: If tool choice creation fails
        """
        return OpenAIToolChoice(function={"name": "Structure"})
