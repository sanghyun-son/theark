"""Configuration management for the theark system."""

import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .types import Environment


class Settings(BaseModel):
    """Application settings."""

    # Environment
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

    # LLM Settings
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

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Set auth_required based on environment
        if self.environment == Environment.PRODUCTION:
            self.auth_required = True

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

    return Settings(
        environment=Environment(os.getenv("THEARK_ENV", "development")),
        api_title=os.getenv("THEARK_API_TITLE", "TheArk API"),
        api_version=os.getenv("THEARK_API_VERSION", "1.0.0"),
        cors_allow_origins=cors_origins,
        auth_required=auth_required,
        auth_header_name=os.getenv("THEARK_AUTH_HEADER", "Authorization"),
        log_level=os.getenv("THEARK_LOG_LEVEL", "INFO"),
        default_summary_language=os.getenv("THEARK_DEFAULT_SUMMARY_LANGUAGE", "Korean"),
        default_interests=os.getenv(
            "THEARK_DEFAULT_INTERESTS", "Machine Learning,Deep Learning"
        ),
        preset_categories=preset_categories,
        arxiv_api_base_url=os.getenv(
            "THEARK_ARXIV_API_BASE_URL", "https://export.arxiv.org/api/query"
        ),
        llm_model=os.getenv("THEARK_LLM_MODEL", "gpt-4o-mini"),
        llm_api_base_url=os.getenv(
            "THEARK_LLM_API_BASE_URL", "https://api.openai.com/v1"
        ),
        llm_use_tools=llm_use_tools,
    )


# Global settings instance
settings = load_settings()
