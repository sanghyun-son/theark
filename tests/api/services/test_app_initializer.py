"""Test AppServiceInitializer class."""

import pytest

from api.services.app_initializer import AppServiceInitializer
from core.config import Settings
from core.types import Environment


@pytest.fixture
def mock_settings() -> Settings:
    """Provide test settings."""
    return Settings(
        environment=Environment.TESTING,
        log_level="INFO",
        auth_required=False,
        historical_crawl_enabled=True,
        historical_crawl_categories=["cs.AI", "cs.LG", "cs.CL"],
        historical_crawl_rate_limit_delay=10.0,
        historical_crawl_batch_size=100,
    )


def test_app_service_initializer_init(mock_settings: Settings):
    """Test AppServiceInitializer initialization."""
    initializer = AppServiceInitializer(mock_settings)
    assert initializer.settings == mock_settings
    assert initializer.engine is None
    assert initializer.arxiv_explorer is None
    assert initializer.historical_crawl_manager is None
    assert initializer.crawl_service is None


@pytest.mark.asyncio
async def test_initialize_crawler_services_success(
    mock_settings: Settings, mock_db_engine
):
    """Test successful crawler service initialization."""
    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)
    initializer.engine = mock_db_engine

    await initializer.initialize_crawler_services()

    assert initializer.arxiv_explorer is not None
    assert initializer.historical_crawl_manager is not None
    assert initializer.crawl_service is not None


@pytest.mark.asyncio
async def test_initialize_crawler_services_with_custom_url(
    mock_settings: Settings, mock_db_engine
):
    """Test crawler service initialization with custom ArXiv URL."""
    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)
    initializer.engine = mock_db_engine

    custom_url = "https://custom.arxiv.org/api/query"
    await initializer.initialize_crawler_services(arxiv_base_url=custom_url)

    assert initializer.arxiv_explorer is not None
    assert initializer.arxiv_explorer.api_base_url == custom_url


@pytest.mark.asyncio
async def test_initialize_crawler_services_no_database(mock_settings: Settings):
    """Test crawler service initialization without database."""
    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)
    # engine is None

    with pytest.raises(
        RuntimeError, match="Database must be initialized before crawler services"
    ):
        await initializer.initialize_crawler_services()


@pytest.mark.asyncio
async def test_initialize_llm_services_success(mock_settings: Settings):
    """Test successful LLM service initialization."""
    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)

    await initializer.initialize_llm_services()

    assert initializer.openai_client is not None


@pytest.mark.asyncio
async def test_initialize_llm_services_with_custom_config(mock_settings: Settings):
    """Test LLM service initialization with custom configuration."""
    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)

    custom_base_url = "https://custom.openai.com/v1"
    custom_api_key = "custom-api-key"

    await initializer.initialize_llm_services(
        llm_base_url=custom_base_url, llm_api_key=custom_api_key
    )

    assert initializer.openai_client is not None


@pytest.mark.asyncio
async def test_initialize_all_services_with_di(
    mock_settings: Settings, mock_db_engine, mock_arxiv_server, mock_openai_server
):
    """Test initialize_all_services with dependency injection."""
    from fastapi import FastAPI

    from api.services.app_initializer import AppServiceInitializer

    app = FastAPI()
    initializer = AppServiceInitializer(mock_settings)

    # Test with custom dependencies using mock servers
    custom_arxiv_url = (
        f"http://{mock_arxiv_server.host}:{mock_arxiv_server.port}/api/query"
    )
    custom_llm_url = f"http://{mock_openai_server.host}:{mock_openai_server.port}/v1"
    custom_llm_key = "test-api-key"

    await initializer.initialize_all_services(
        app=app,
        engine=mock_db_engine,
        arxiv_base_url=custom_arxiv_url,
        llm_base_url=custom_llm_url,
        llm_api_key=custom_llm_key,
    )

    # Verify all services are initialized
    assert initializer.engine == mock_db_engine
    assert initializer.arxiv_explorer is not None
    assert initializer.arxiv_explorer.api_base_url == custom_arxiv_url
    assert initializer.historical_crawl_manager is not None
    assert initializer.crawl_service is not None
    assert initializer.openai_client is not None
    assert initializer.background_batch_manager is not None

    # Verify app.state is configured
    assert app.state.engine == mock_db_engine
    assert app.state.arxiv_explorer == initializer.arxiv_explorer
    assert app.state.historical_crawl_manager == initializer.historical_crawl_manager
    assert app.state.crawl_service == initializer.crawl_service
    assert app.state.summary_client == initializer.openai_client
    assert app.state.background_batch_manager == initializer.background_batch_manager


@pytest.mark.asyncio
async def test_initialize_all_services_without_di(mock_settings: Settings):
    """Test initialize_all_services without dependency injection (uses defaults)."""
    from fastapi import FastAPI

    from api.services.app_initializer import AppServiceInitializer

    app = FastAPI()
    initializer = AppServiceInitializer(mock_settings)

    # Test without custom dependencies (should use settings defaults)
    await initializer.initialize_all_services(app=app)

    # Verify all services are initialized with default settings
    assert initializer.engine is not None
    assert initializer.arxiv_explorer is not None
    assert initializer.arxiv_explorer.api_base_url == mock_settings.arxiv_api_base_url
    assert initializer.historical_crawl_manager is not None
    assert initializer.crawl_service is not None
    assert initializer.openai_client is not None
    assert initializer.background_batch_manager is not None


@pytest.mark.asyncio
async def test_start_all_services_success(
    mock_settings: Settings, mock_db_engine, mock_openai_client
):
    """Test successful start of all background services."""
    from unittest.mock import AsyncMock

    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)
    initializer.engine = mock_db_engine
    initializer.openai_client = mock_openai_client

    # Mock background_batch_manager with proper async methods
    mock_batch_manager = AsyncMock()
    initializer.background_batch_manager = mock_batch_manager

    # Test start_all_services
    await initializer.start_all_services()

    # Verify start method was called
    mock_batch_manager.start.assert_called_once_with(
        db_engine=mock_db_engine,
        openai_client=mock_openai_client,
    )


@pytest.mark.asyncio
async def test_start_all_services_no_database(mock_settings: Settings):
    """Test start_all_services without database."""
    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)
    # engine is None

    with pytest.raises(
        RuntimeError, match="Database must be initialized before starting services"
    ):
        await initializer.start_all_services()


@pytest.mark.asyncio
async def test_start_all_services_no_llm(mock_settings: Settings, mock_db_engine):
    """Test start_all_services without LLM services."""
    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)
    initializer.engine = mock_db_engine
    # openai_client is None

    with pytest.raises(
        RuntimeError, match="LLM services must be initialized before starting services"
    ):
        await initializer.start_all_services()


@pytest.mark.asyncio
async def test_stop_all_services_success(mock_settings: Settings):
    """Test successful stop of all background services."""
    from unittest.mock import AsyncMock

    from api.services.app_initializer import AppServiceInitializer

    initializer = AppServiceInitializer(mock_settings)

    # Mock background_batch_manager with proper async methods
    mock_batch_manager = AsyncMock()
    initializer.background_batch_manager = mock_batch_manager

    # Test stop_all_services
    await initializer.stop_all_services()

    # Verify stop method was called
    mock_batch_manager.stop.assert_called_once()
