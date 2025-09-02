"""Configuration management for the theark system."""

import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .types import Environment


class Settings(BaseModel):
    """Application settings."""

    # Environment
    version: str = Field(default="0.1.0", description="Application version")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment (development/production/testing)",
    )

    # API Settings
    api_title: str = Field(default="TheArk API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")

    # CORS Settings
    cors_allow_origins: list[str] = Field(
        default=["*"], description="Allowed CORS origins"
    )

    # Auth Settings
    auth_required: bool = Field(
        default=False, description="Whether authentication is required"
    )
    auth_header_name: str = Field(
        default="Authorization", description="Authentication header name"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Summarization Settings
    default_summary_language: str = Field(
        default="Korean", description="Default language for paper summaries"
    )
    default_interests: str = Field(
        default="Machine Learning,Deep Learning",
        description="Default interests for paper relevance scoring",
    )

    # Paper Filtering Settings
    preset_categories: list[str] = Field(
        default=["cs.AI", "cs.CL", "cs.CV", "cs.DC", "cs.IR", "cs.LG", "cs.MA"],
        description="Preset categories for paper filtering",
    )

    # ArXiv Settings
    arxiv_api_base_url: str = Field(
        default="https://export.arxiv.org/api/query", description="ArXiv API full URL"
    )
    arxiv_delay_seconds: float = Field(
        default=2.0, description="Delay between ArXiv API requests in seconds"
    )
    arxiv_max_results_per_request: int = Field(
        default=100, description="Maximum results per ArXiv API request"
    )

    # Historical Crawl Settings
    historical_crawl_enabled: bool = Field(
        default=False, description="Whether historical crawling is enabled"
    )
    historical_crawl_categories: list[str] = Field(
        default=["cs.AI", "cs.LG", "cs.CL"],
        description="Default categories for historical crawling",
    )
    historical_crawl_start_date: str | None = Field(
        default=None, description="Start date for historical crawling (YYYY-MM-DD)"
    )
    historical_crawl_rate_limit_delay: float = Field(
        default=10.0, description="Delay between historical crawl requests in seconds"
    )
    historical_crawl_batch_size: int = Field(
        default=100, description="Number of papers per historical crawl request"
    )

    # LLM Settings
    llm_api_key: str = Field(
        default="", description="LLM API key from environment variable"
    )
    llm_model: str = Field(
        default="gpt-4o-mini", description="LLM model to use for summarization"
    )
    llm_api_base_url: str = Field(
        default="https://api.openai.com/v1", description="LLM API base URL"
    )
    llm_use_tools: bool = Field(
        default=True,
        description="Whether to use function calling for structured output",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for OpenAI API requests",
    )

    # Batch Processing Settings
    batch_summary_interval: int = Field(
        default=3600, description="Interval in seconds for summary batch processing"
    )
    batch_fetch_interval: int = Field(
        default=600, description="Interval in seconds for fetching batch results"
    )
    batch_max_items: int = Field(
        default=1000, description="Maximum number of items per batch"
    )
    batch_daily_limit: int = Field(
        default=10000, description="Maximum number of requests per day"
    )
    batch_enabled: bool = Field(
        default=True, description="Whether batch processing is enabled"
    )
    batch_max_retries: int = Field(
        default=3, description="Maximum number of retries for failed batches"
    )
    # ArXiv background explorer settings
    arxiv_categories: list[str] = Field(
        default=["cs.AI", "cs.CL", "cs.CV", "cs.DC", "cs.IR", "cs.LG", "cs.MA"],
        description="ArXiv categories to explore (same as preset_categories)",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Set auth_required based on environment
        if self.environment == Environment.PRODUCTION:
            self.auth_required = True
        else:  # DEVELOPMENT and TESTING
            self.auth_required = False

        # Override historical_crawl_enabled for testing environment
        if self.environment == Environment.TESTING:
            self.historical_crawl_enabled = True

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == Environment.TESTING

    @property
    def arxiv_url(self) -> str:
        """Get the correct arXiv URL based on environment.

        For dev/prod: returns the full URL from arxiv_api_base_url
        For testing: should be overridden by test fixtures
        """
        return self.arxiv_api_base_url

    @property
    def default_interests_list(self) -> list[str]:
        """Get default interests as a list."""
        return [interest.strip() for interest in self.default_interests.split(",")]


def load_settings() -> Settings:
    """Load settings from environment variables."""

    # Load .env file if it exists
    load_dotenv()

    # Parse CORS origins from comma-separated string
    cors_origins_str = os.getenv("THEARK_CORS_ORIGINS", "*")
    if cors_origins_str == "*":
        cors_origins = ["*"]
    else:
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

    auth_required = os.getenv("THEARK_AUTH_REQUIRED", "false").lower() == "true"

    # Parse preset categories from comma-separated string
    preset_categories_str = os.getenv(
        "THEARK_PRESET_CATEGORIES", "cs.AI,cs.CL,cs.CV,cs.DC,cs.IR,cs.LG,cs.MA"
    )
    preset_categories = [cat.strip() for cat in preset_categories_str.split(",")]

    # Parse LLM use_tools from boolean string
    llm_use_tools = os.getenv("THEARK_LLM_USE_TOOLS", "true").lower() == "true"

    # Parse batch settings
    batch_summary_interval = int(os.getenv("THEARK_BATCH_SUMMARY_INTERVAL", "3600"))
    batch_fetch_interval = int(os.getenv("THEARK_BATCH_FETCH_INTERVAL", "600"))
    batch_max_items = int(os.getenv("THEARK_BATCH_MAX_ITEMS", "1000"))
    batch_daily_limit = int(os.getenv("THEARK_BATCH_DAILY_LIMIT", "10000"))
    batch_enabled_str = os.getenv("THEARK_BATCH_ENABLED", "false").lower()
    batch_enabled = batch_enabled_str in ["true", "1", "yes", "on"]
    batch_max_retries = int(os.getenv("THEARK_BATCH_MAX_RETRIES", "3"))

    # Parse ArXiv settings
    # Use the same categories as preset_categories for consistency
    arxiv_categories = preset_categories

    # Parse Historical Crawl settings
    historical_crawl_enabled = os.getenv(
        "THEARK_HISTORICAL_CRAWL_ENABLED", "false"
    ).lower() in ["true", "1", "yes", "on"]
    # Use the same categories as preset_categories for consistency
    historical_crawl_categories = preset_categories
    historical_crawl_start_date = os.getenv("THEARK_HISTORICAL_CRAWL_START_DATE")
    historical_crawl_rate_limit_delay = float(
        os.getenv("THEARK_HISTORICAL_CRAWL_RATE_LIMIT_DELAY", "10.0")
    )
    historical_crawl_batch_size = int(
        os.getenv("THEARK_HISTORICAL_CRAWL_BATCH_SIZE", "100")
    )

    return Settings(
        environment=Environment(os.getenv("THEARK_ENV", "development")),
        api_title=os.getenv("THEARK_API_TITLE", "TheArk API"),
        api_version=os.getenv("THEARK_API_VERSION", "1.0.0"),
        cors_allow_origins=cors_origins,
        auth_required=auth_required,
        auth_header_name=os.getenv("THEARK_AUTH_HEADER", "Authorization"),
        log_level=os.getenv("THEARK_LOG_LEVEL", "INFO").upper(),
        default_summary_language=os.getenv("THEARK_DEFAULT_SUMMARY_LANGUAGE", "Korean"),
        default_interests=os.getenv(
            "THEARK_DEFAULT_INTERESTS", "Machine Learning,Deep Learning"
        ),
        preset_categories=preset_categories,
        arxiv_api_base_url=os.getenv(
            "THEARK_ARXIV_API_BASE_URL", "https://export.arxiv.org/api/query"
        ),
        llm_api_key=os.getenv("OPENAI_API_KEY", "*"),
        llm_model=os.getenv("THEARK_LLM_MODEL", "gpt-4o-mini"),
        llm_api_base_url=os.getenv(
            "THEARK_LLM_API_BASE_URL", "https://api.openai.com/v1"
        ),
        llm_use_tools=llm_use_tools,
        max_retries=int(os.getenv("THEARK_LLM_MAX_RETRIES", "3")),
        batch_summary_interval=batch_summary_interval,
        batch_fetch_interval=batch_fetch_interval,
        batch_max_items=batch_max_items,
        batch_daily_limit=batch_daily_limit,
        batch_enabled=batch_enabled,
        batch_max_retries=batch_max_retries,
        arxiv_categories=arxiv_categories,
        historical_crawl_enabled=historical_crawl_enabled,
        historical_crawl_categories=historical_crawl_categories,
        historical_crawl_start_date=historical_crawl_start_date,
        historical_crawl_rate_limit_delay=historical_crawl_rate_limit_delay,
        historical_crawl_batch_size=historical_crawl_batch_size,
    )


# Global settings instance
settings = load_settings()
