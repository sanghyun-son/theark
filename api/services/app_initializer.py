"""Application service initializer for managing startup and shutdown."""

from typing import Any

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from core.config import Settings
from core.database.engine import create_database_engine, create_database_tables
from core.extractors.concrete.arxiv_extractor import ArxivExtractor
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.extractors.concrete.historical_crawl_manager import HistoricalCrawlManager
from core.extractors.factory import register_extractor
from core.llm.openai_client import UnifiedOpenAIClient
from core.log import get_logger
from core.services.crawl_service import CrawlService

logger = get_logger(__name__)


class AppServiceInitializer:
    """Manages initialization and lifecycle of application services."""

    def __init__(self, settings: Settings):
        """Initialize with application settings."""
        self.settings = settings
        self.engine: Engine | None = None
        self.arxiv_explorer: ArxivSourceExplorer | None = None
        self.historical_crawl_manager: HistoricalCrawlManager | None = None
        self.crawl_service: CrawlService | None = None
        self.openai_client: UnifiedOpenAIClient | None = None
        self.background_batch_manager: Any | None = None

    async def initialize_all_services(
        self,
        app: FastAPI,
        engine: Engine | None = None,
        arxiv_base_url: str | None = None,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
    ) -> None:
        """Initialize all services and configure app.state."""
        logger.info("Initializing all application services...")

        await self.initialize_database(engine)
        await self.initialize_crawler_services(arxiv_base_url)
        await self.initialize_llm_services(llm_base_url, llm_api_key)
        await self.initialize_batch_services()
        self._setup_app_state(app)

        logger.info("All application services initialized successfully")

    async def initialize_database(self, engine: Engine | None = None) -> None:
        """Initialize database engine and create tables."""
        logger.info("Initializing database...")

        if engine:
            self.engine = engine
        else:
            self.engine = create_database_engine(self.settings.environment)

        create_database_tables(self.engine)

        logger.info("Database initialized successfully")

    async def initialize_crawler_services(
        self, arxiv_base_url: str | None = None
    ) -> None:
        """Initialize crawler-related services."""
        if not self.engine:
            raise RuntimeError("Database must be initialized before crawler services")

        # Initialize ArXiv source explorer
        base_url = arxiv_base_url or self.settings.arxiv_api_base_url
        self.arxiv_explorer = ArxivSourceExplorer(
            api_base_url=base_url,
            delay_seconds=self.settings.arxiv_delay_seconds,
            max_results_per_request=self.settings.arxiv_max_results_per_request,
        )

        # Initialize historical crawl manager only if enabled
        if self.settings.historical_crawl_enabled:
            self.historical_crawl_manager = HistoricalCrawlManager(
                categories=self.settings.historical_crawl_categories,
                rate_limit_delay=self.settings.historical_crawl_rate_limit_delay,
                batch_size=self.settings.historical_crawl_batch_size,
            )
        else:
            logger.warning("Historical crawling is disabled")
            self.historical_crawl_manager = None

        # Initialize crawl service
        self.crawl_service = (
            CrawlService(self.historical_crawl_manager)
            if self.historical_crawl_manager
            else None
        )

        # Register ArXiv extractor
        arxiv_extractor = ArxivExtractor(api_base_url=base_url)
        register_extractor("arxiv", arxiv_extractor)

    async def initialize_llm_services(
        self, llm_base_url: str | None = None, llm_api_key: str | None = None
    ) -> None:
        """Initialize LLM-related services."""

        # Initialize OpenAI client
        base_url = llm_base_url or self.settings.llm_api_base_url
        api_key = llm_api_key or self.settings.llm_api_key

        self.openai_client = UnifiedOpenAIClient(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0,
            model=self.settings.llm_model,
            use_tools=self.settings.llm_use_tools,
        )

    async def initialize_batch_services(self) -> None:
        """Initialize batch processing services."""

        if not self.engine:
            raise RuntimeError("Database must be initialized before batch services")

        # Initialize background batch manager
        from core.batch.background_manager import BackgroundBatchManager
        from core.services.summarization_service import PaperSummarizationService

        # Create summarization service first
        summary_service = PaperSummarizationService()

        if self.settings.batch_enabled:
            self.background_batch_manager = BackgroundBatchManager(
                summary_service=summary_service,
                batch_summary_interval=self.settings.batch_summary_interval,
                batch_fetch_interval=self.settings.batch_fetch_interval,
                batch_max_items=self.settings.batch_max_items,
                batch_daily_limit=self.settings.batch_daily_limit,
                language=self.settings.default_summary_language,
                interests=self.settings.default_interests_list,
            )
        else:
            logger.warning("Batch processing is disabled")
            self.background_batch_manager = None

    async def start_all_services(self) -> None:
        """Start all background services."""
        logger.info("Starting all background services...")

        if not self.engine:
            raise RuntimeError("Database must be initialized before starting services")

        if not self.openai_client:
            raise RuntimeError(
                "LLM services must be initialized before starting services"
            )

        # Start historical crawl manager if available
        if self.historical_crawl_manager and self.arxiv_explorer:
            await self.historical_crawl_manager.start(self.arxiv_explorer, self.engine)

        # Start background batch manager if available
        if self.background_batch_manager:
            await self.background_batch_manager.start(
                db_engine=self.engine,
                openai_client=self.openai_client,
            )

        logger.info("All background services started successfully")

    async def stop_all_services(self) -> None:
        """Stop all background services."""
        logger.info("Stopping all background services...")

        # Stop historical crawl manager if available
        if self.historical_crawl_manager:
            await self.historical_crawl_manager.stop()

        # Stop background batch manager if available
        if self.background_batch_manager:
            await self.background_batch_manager.stop()

        logger.info("All background services stopped successfully")

    def _setup_app_state(self, app: FastAPI) -> None:
        """Configure app.state with initialized services."""
        # Store services in app.state for dependency injection
        app.state.engine = self.engine
        app.state.arxiv_explorer = self.arxiv_explorer
        app.state.historical_crawl_manager = self.historical_crawl_manager
        app.state.crawl_service = self.crawl_service
        app.state.summary_client = self.openai_client
        app.state.background_batch_manager = self.background_batch_manager
