"""Paper service for CRUD operations."""

import asyncio
import re
from typing import Any, Optional

from core import get_logger
from core.config import load_settings
from core.models import PaperCreateRequest as PaperCreate
from core.models import (
    PaperDeleteResponse,
    PaperListResponse,
    PaperResponse,
    SummaryEntity,
    SummaryReadResponse,
)
from core.models.database.entities import PaperEntity
from crawler.arxiv.on_demand_crawler import OnDemandCrawlConfig, OnDemandCrawler
from crawler.database import (
    PaperRepository,
    SummaryRepository,
)
from crawler.database.sqlite_manager import SQLiteManager
from crawler.summarizer.service import SummarizationService

logger = get_logger(__name__)


class PaperService:
    """Service for paper CRUD operations."""

    def __init__(
        self, db_manager: SQLiteManager | None = None, llm_db_manager: Any = None
    ) -> None:
        """Initialize paper service."""
        self.db_manager = db_manager
        self.llm_db_manager = llm_db_manager
        self.settings = load_settings()
        self.paper_repo: PaperRepository | None = None
        self.summary_repo: SummaryRepository | None = None
        self.summarization_service: SummarizationService | None = None

        self._initialize_repositories()
        self._initialize_summarization_service()

    def _initialize_repositories(self) -> None:
        """Initialize database repositories."""
        if self.db_manager:
            self.paper_repo = PaperRepository(self.db_manager)
            self.summary_repo = SummaryRepository(self.db_manager)

    def _initialize_summarization_service(self) -> None:
        """Initialize summarization service."""
        try:
            self.summarization_service = SummarizationService(
                model=self.settings.llm_model,
                base_url=self.settings.llm_api_base_url,
                use_tools=self.settings.llm_use_tools,
                db_manager=self.llm_db_manager,
            )
            logger.info(
                f"SummarizationService successfully initialized with "
                f"model={self.settings.llm_model}, "
                f"base_url={self.settings.llm_api_base_url}, "
                f"use_tools={self.settings.llm_use_tools}"
            )
        except ValueError as e:
            logger.warning(f"SummarizationService not initialized: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error initializing SummarizationService: {e}",
                exc_info=True,
            )

    async def create_paper(
        self, paper_data: PaperCreate, skip_auto_summarization: bool = False
    ) -> PaperResponse:
        """Create a new paper."""
        arxiv_id = self._extract_arxiv_id(paper_data)

        existing_paper = self._get_paper_by_arxiv_id(arxiv_id)
        if existing_paper and not paper_data.force_refresh_metadata:
            logger.info(f"Paper {arxiv_id} already exists, returning existing paper")
            return PaperResponse.from_crawler_paper(existing_paper)

        crawled_paper = await self._crawl_paper(arxiv_id)

        # Only start summarization if not skipped (e.g., when using streaming)
        if paper_data.summarize_now and not skip_auto_summarization:
            self._start_summarization(crawled_paper, paper_data)

        return PaperResponse.from_crawler_paper(crawled_paper, None)

    async def _crawl_paper(self, arxiv_id: str) -> PaperEntity:
        """Crawl a single paper from arXiv."""
        if not self.db_manager:
            raise ValueError("Database manager not available")

        crawler_config = OnDemandCrawlConfig()
        async with OnDemandCrawler(
            db_manager=self.db_manager, config=crawler_config
        ) as crawler:
            crawled_paper = await crawler.crawl_single_paper(arxiv_id)
            if not crawled_paper:
                raise ValueError(f"Failed to crawl paper {arxiv_id}")

            logger.info(f"Successfully crawled paper {arxiv_id}")
            return crawled_paper

    def _start_summarization(
        self, crawled_paper: PaperEntity, paper_data: PaperCreate
    ) -> None:
        """Start background summarization for a paper."""
        if not self.summarization_service:
            return

        try:
            asyncio.create_task(
                self._summarize_paper_async(
                    crawled_paper,
                    paper_data.force_resummarize,
                    paper_data.summary_language,
                )
            )
            logger.info(
                f"Started background summarization for paper "
                f"{crawled_paper.arxiv_id} in {paper_data.summary_language}"
            )
        except Exception as e:
            logger.error(
                f"Failed to start summarization for paper {crawled_paper.arxiv_id}: {e}"
            )

    async def get_paper(self, paper_identifier: str) -> PaperResponse:
        """Get a paper by ID or arXiv ID."""
        paper = self._get_paper_by_identifier(paper_identifier)
        if not paper:
            raise ValueError(f"Paper not found: {paper_identifier}")

        summary = self._get_paper_summary(paper)
        return PaperResponse.from_crawler_paper(paper, summary)

    def _get_paper_summary(
        self, paper: PaperEntity, language: str = "Korean"
    ) -> Optional[SummaryEntity]:
        """Get summary for a paper in specified language."""
        if not paper.paper_id:
            return None

        try:
            self._ensure_db_connection(paper.arxiv_id)
            if not self.summary_repo:
                return None

            summary_obj = self.summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )
            if not summary_obj and language != "English":
                summary_obj = self.summary_repo.get_by_paper_and_language(
                    paper.paper_id, "English"
                )

            if not summary_obj:
                return None

            return summary_obj
        except Exception as e:
            logger.error(f"Error getting paper summary for {paper.arxiv_id}: {e}")
            return None

    def _format_summary(self, summary_obj: SummaryEntity) -> str:
        """Format summary object into readable text."""
        summary_parts = []
        if summary_obj.overview:
            summary_parts.append(f"Overview: {summary_obj.overview}")
        if summary_obj.motivation:
            summary_parts.append(f"Motivation: {summary_obj.motivation}")
        if summary_obj.method:
            summary_parts.append(f"Method: {summary_obj.method}")
        if summary_obj.result:
            summary_parts.append(f"Result: {summary_obj.result}")
        if summary_obj.conclusion:
            summary_parts.append(f"Conclusion: {summary_obj.conclusion}")

        return "\n\n".join(summary_parts)

    async def delete_paper(self, paper_identifier: str) -> PaperDeleteResponse:
        """Delete a paper by ID or arXiv ID."""
        paper = self._get_paper_by_identifier(paper_identifier)
        if not paper:
            raise ValueError(f"Paper not found: {paper_identifier}")

        if not paper.paper_id:
            raise ValueError("Paper ID not available")

        try:
            self._ensure_db_connection(paper.arxiv_id)

            if not self.paper_repo:
                raise ValueError("Paper repository not available")

            if self.summary_repo:
                summaries = self.summary_repo.get_by_paper_id(paper.paper_id)
                for summary in summaries:
                    if summary.summary_id is not None:
                        self.summary_repo.delete(summary.summary_id)
                logger.info(
                    f"Deleted {len(summaries)} summaries for paper {paper.arxiv_id}"
                )

            self.paper_repo.delete(paper.paper_id)
            logger.info(
                f"Successfully deleted paper {paper.arxiv_id} (ID: {paper.paper_id})"
            )

            return PaperDeleteResponse(
                success=True,
                message=f"Paper {paper.arxiv_id} deleted successfully",
            )
        except Exception as e:
            logger.error(f"Error deleting paper {paper.arxiv_id}: {e}")
            raise ValueError(f"Failed to delete paper: {e}")

    async def get_papers(
        self, limit: int = 20, offset: int = 0, language: str = "Korean"
    ) -> "PaperListResponse":
        """Get papers with pagination."""
        try:
            self._ensure_db_connection("papers_list")

            if not self.paper_repo:
                raise ValueError("Paper repository not available")

            papers, total_count = self.paper_repo.get_papers_paginated(limit, offset)

            paper_responses = []
            for paper in papers:
                summary = self._get_paper_summary(paper, language)
                paper_response = PaperResponse.from_crawler_paper(paper, summary)
                paper_responses.append(paper_response)

            has_more = (offset + limit) < total_count

            return PaperListResponse(
                papers=paper_responses,
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_more=has_more,
            )

        except Exception as e:
            logger.error(f"Error getting papers: {e}")
            raise ValueError(f"Failed to get papers: {e}")

    def _extract_arxiv_id(self, paper_data: PaperCreate) -> str:
        """Extract arXiv ID from paper data."""
        if paper_data.url:
            match = re.search(r"/abs/(\d{4}\.\d{5})$", paper_data.url)
            if match:
                return match.group(1)
            raise ValueError("Could not extract arXiv ID from URL")

        raise ValueError("No URL provided")

    def _get_paper_by_arxiv_id(self, arxiv_id: str) -> PaperEntity | None:
        """Get paper by arXiv ID.

        Args:
            arxiv_id: arXiv ID

        Returns:
            Paper if found, None otherwise
        """
        if not self.db_manager or not self.paper_repo:
            return None

        try:
            return self.paper_repo.get_by_arxiv_id(arxiv_id)
        except Exception as e:
            logger.error(f"Error getting paper by arXiv ID {arxiv_id}: {e}")
            return None

    def _get_paper_by_identifier(self, identifier: str) -> PaperEntity | None:
        """Get paper by ID or arXiv ID."""
        try:
            self._ensure_db_connection(identifier)

            if not self.paper_repo:
                return None

            paper = self.paper_repo.get_by_arxiv_id(identifier)
            if paper:
                return paper

            int(identifier)
            return None
        except ValueError:
            return None
        except Exception as e:
            logger.error(f"Error getting paper by identifier {identifier}: {e}")
            return None

    async def _summarize_paper_async(
        self,
        paper: PaperEntity,
        force_resummarize: bool = False,
        language: str = "Korean",
    ) -> None:
        """Summarize paper asynchronously."""
        if not self.summarization_service:
            logger.warning("SummarizationService not available")
            return

        try:
            logger.info(
                f"Starting summarization for paper {paper.arxiv_id} "
                f"(ID: {paper.paper_id})"
            )

            if self._summary_exists(paper, language, force_resummarize):
                return

            summary_response = await self._generate_summary(paper, language)
            if not summary_response:
                return

            await self._save_summary(paper, summary_response, language)

        except Exception as e:
            logger.error(f"Error summarizing paper {paper.arxiv_id}: {e}")

    def _ensure_db_connection(self, arxiv_id: str) -> None:
        """Ensure database connection is active."""
        if not self.db_manager:
            logger.error(f"No database manager available for paper {arxiv_id}")
            raise ValueError("Database manager not available")

        try:
            self.db_manager.execute("SELECT 1")
            if not self.paper_repo or not self.summary_repo:
                self._initialize_repositories()
        except Exception:
            try:
                logger.info(f"Reconnecting database for paper {arxiv_id}")
                self.db_manager.connect()
                self._initialize_repositories()
            except Exception as e:
                logger.error(f"Failed to connect database for paper {arxiv_id}: {e}")
                raise ValueError(f"Database connection failed: {e}")

    def _summary_exists(
        self, paper: PaperEntity, language: str, force_resummarize: bool
    ) -> bool:
        """Check if summary already exists."""
        if not paper.paper_id:
            return False

        if force_resummarize:
            logger.info(
                f"Force resummarize requested for paper {paper.arxiv_id} in {language}"
            )
            return False

        try:
            self._ensure_db_connection(paper.arxiv_id)

            if not self.summary_repo:
                return False

            existing_summary = self.summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )
            if existing_summary:
                logger.info(
                    f"Summary already exists for paper {paper.arxiv_id} in {language}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking summary existence for {paper.arxiv_id}: {e}")
            return False

    async def _generate_summary(
        self, paper: PaperEntity, language: str
    ) -> Optional[Any]:
        """Generate summary using the summarization service."""
        logger.info(f"Calling summarization service for paper {paper.arxiv_id}")

        if not self.summarization_service:
            logger.error(
                f"No summarization service available for paper {paper.arxiv_id}"
            )
            return None

        if not paper.abstract:
            logger.error(f"No abstract available for paper {paper.arxiv_id}")
            return None

        try:
            summary_response = await self.summarization_service.summarize_paper(
                paper_id=str(paper.paper_id),
                abstract=paper.abstract,
                language=language,
                interest_section=self.settings.default_interests,
            )

            logger.info(
                f"Summary response received for paper {paper.arxiv_id}: "
                f"{summary_response is not None}"
            )
            return summary_response
        except Exception as e:
            logger.error(
                f"Error generating summary for paper {paper.arxiv_id}: {e}",
                exc_info=True,
            )
            return None

    async def _save_summary(
        self, paper: PaperEntity, summary_response: Any, language: str
    ) -> None:
        """Save summary to database."""
        if not paper.paper_id:
            logger.error(f"No paper ID available for paper {paper.arxiv_id}")
            return

        try:
            self._ensure_db_connection(paper.arxiv_id)

            if not self.summary_repo:
                logger.error(
                    f"No summary repository available for paper {paper.arxiv_id}"
                )
                return

            existing_summary = self.summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )
            if existing_summary and existing_summary.summary_id:
                logger.info(
                    f"Deleting existing summary for paper {paper.arxiv_id} "
                    f"in {language}"
                )
                self.summary_repo.delete(existing_summary.summary_id)

            logger.info(f"Creating Summary model for paper {paper.arxiv_id}")
            summary = self._create_summary_model(paper, summary_response, language)
            summary_id = self.summary_repo.create(summary)
            logger.info(
                f"Successfully saved summary {summary_id} for paper {paper.arxiv_id}"
            )
        except Exception as db_error:
            logger.error(
                f"Database error saving summary for paper {paper.arxiv_id}: {db_error}"
            )
            raise

    def _create_summary_model(
        self, paper: PaperEntity, summary_response: Any, language: str
    ) -> SummaryEntity:
        """Create Summary model from response."""
        structured_data = summary_response.structured_summary

        if structured_data:
            logger.info(f"Using structured summary data for paper {paper.arxiv_id}")
            return SummaryEntity(
                paper_id=paper.paper_id or 0,
                version=1,
                overview=structured_data.tldr or "",
                motivation=structured_data.motivation or "",
                method=structured_data.method or "",
                result=structured_data.result or "",
                conclusion=structured_data.conclusion or "",
                language=language,
                interests=self.settings.default_interests,
                relevance=(
                    int(float(structured_data.relevance))
                    if structured_data.relevance
                    and structured_data.relevance.replace(".", "").isdigit()
                    else 0
                ),
                model=(
                    summary_response.metadata.get("model", "unknown")
                    if summary_response.metadata
                    else "unknown"
                ),
                is_read=False,  # New summaries are unread by default
            )
        else:
            logger.info(f"Using simple summary data for paper {paper.arxiv_id}")
            return SummaryEntity(
                paper_id=paper.paper_id or 0,
                version=1,
                overview=summary_response.summary or "",
                motivation="",
                method="",
                result="",
                conclusion="",
                language=language,
                interests=self.settings.default_interests,
                relevance=0,
                model=(
                    summary_response.metadata.get("model", "unknown")
                    if summary_response.metadata
                    else "unknown"
                ),
                is_read=False,  # New summaries are unread by default
            )

    async def get_summary(self, paper_id: int, summary_id: int) -> SummaryEntity:
        """Get a specific summary by ID.

        Args:
            paper_id: Paper ID
            summary_id: Summary ID

        Returns:
            Summary details

        Raises:
            ValueError: If summary not found or doesn't belong to the paper
        """
        self._ensure_db_connection(f"paper_{paper_id}")

        if not self.summary_repo:
            raise ValueError("Summary repository not available")

        summary = self.summary_repo.get_by_id(summary_id)
        if not summary:
            raise ValueError(f"Summary {summary_id} not found")

        if summary.paper_id != paper_id:
            raise ValueError(
                f"Summary {summary_id} does not belong to paper {paper_id}"
            )

        return summary

    async def mark_summary_as_read(
        self, paper_id: int, summary_id: int
    ) -> "SummaryReadResponse":
        """Mark a summary as read.

        Args:
            paper_id: Paper ID
            summary_id: Summary ID

        Returns:
            Success status and updated read status

        Raises:
            ValueError: If summary not found or doesn't belong to the paper
        """
        self._ensure_db_connection(f"paper_{paper_id}")

        if not self.summary_repo:
            raise ValueError("Summary repository not available")

        summary = self.summary_repo.get_by_id(summary_id)
        if not summary:
            raise ValueError(f"Summary {summary_id} not found")

        if summary.paper_id != paper_id:
            raise ValueError(
                f"Summary {summary_id} does not belong to paper {paper_id}"
            )

        # Update the summary to mark it as read
        summary.is_read = True
        self.summary_repo.update(summary)

        return SummaryReadResponse(
            success=True,
            message=f"Summary {summary_id} marked as read",
            summary_id=summary_id,
            is_read=True,
        )

    async def close(self) -> None:
        """Close the service and cleanup resources."""
        if self.summarization_service:
            await self.summarization_service.close()
        logger.info("PaperService closed")
