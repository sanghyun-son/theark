"""Summarization service for paper abstracts."""

import asyncio
import os
from typing import Any

import httpx

from core import get_logger
from crawler.summarizer import (
    OpenAISummarizer,
    SummaryRequest,
    SummaryResponse,
)

logger = get_logger(__name__)


class SummarizationService:
    """Service for managing paper summarization."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        use_tools: bool = True,
        model: str = "gpt-4o-mini",
        db_manager: Any = None,
    ):
        """Initialize the summarization service.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: OpenAI API base URL (for testing with mock server)
            use_tools: Whether to use function calling for structured output
            model: OpenAI model to use for summarization
            db_manager: Optional LLM database manager instance
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or "https://api.openai.com/v1"
        self.use_tools = use_tools
        self.model = model
        self.db_manager = db_manager

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided and OPENAI_API_KEY environment "
                "variable not set"
            )

        logger.info(
            f"SummarizationService initialized with model={model}, "
            f"use_tools={use_tools}, base_url={self.base_url}"
        )

    async def summarize_paper(
        self,
        paper_id: str,
        abstract: str,
        language: str = "English",
        interest_section: str = "",
    ) -> SummaryResponse | None:
        """Summarize a paper's abstract.

        Args:
            paper_id: Unique identifier for the paper
            abstract: The paper's abstract text
            language: Language for the summary
            interest_section: User's interest section for relevance scoring

        Returns:
            SummaryResponse with structured or text summary, or None if failed
        """
        try:
            logger.info(f"Summarizing paper {paper_id}")

            # Create summarizer
            if not self.api_key:
                raise ValueError("API key is required for summarization")
            summarizer = OpenAISummarizer(
                api_key=self.api_key, base_url=self.base_url, db_manager=self.db_manager
            )

            # Create summary request
            request = SummaryRequest(
                custom_id=paper_id,
                content=abstract,
                language=language,
                interest_section=interest_section,
                use_tools=self.use_tools,
                model=self.model,
            )

            # Get summary from OpenAI with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await summarizer.summarize(request)
                    logger.info(f"Successfully summarized paper {paper_id}")
                    return response
                except httpx.ReadTimeout as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                        logger.warning(
                            f"Timeout on attempt {attempt + 1} for paper {paper_id}, "
                            f"retrying in {wait_time} seconds: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All retry attempts failed for paper {paper_id}: {e}"
                        )
                        raise
                except Exception as e:
                    logger.error(
                        f"Failed to summarize paper {paper_id}: {e}", exc_info=True
                    )
                    raise

            # This should never be reached, but mypy needs it
            return None

        except Exception as e:
            logger.error(f"Failed to summarize paper {paper_id}: {e}", exc_info=True)
            return None

    async def close(self) -> None:
        """Close the summarization service and cleanup resources."""
        # No cleanup needed since summarizer is created per request
        logger.info("SummarizationService closed")
