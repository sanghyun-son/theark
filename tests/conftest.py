"""Global pytest configuration and fixtures."""

import json
from collections.abc import Generator
from logging import Logger
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from pytest_httpserver import HTTPServer
from sqlalchemy.engine import Engine
from sqlmodel import Session
from werkzeug.wrappers import Request, Response

from core import setup_test_logging
from core.batch.background_manager import BackgroundBatchManager
from core.database.engine import create_database_tables
from core.database.repository import (
    LLMBatchRepository,
    PaperRepository,
    SummaryReadRepository,
    SummaryRepository,
    UserRepository,
    UserStarRepository,
)
from core.extractors.concrete.arxiv_extractor import ArxivExtractor
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.llm.openai_client import UnifiedOpenAIClient
from core.models.domain.arxiv import ArxivPaper
from core.models.rows import Paper, Summary, User
from core.services.summarization_service import PaperSummarizationService
from core.types import PaperSummaryStatus
from tests.shared_test_data import ARXIV_RESPONSES, OPENAI_RESPONSES


@pytest.fixture(scope="session", autouse=True)
def setup_logging() -> None:
    """Setup test logging for all tests."""
    setup_test_logging()


@pytest.fixture(scope="function")
def logger() -> Logger:
    """Provide a logger instance for tests."""
    from core import get_logger

    return get_logger("test")


@pytest.fixture
def mock_openai_server(httpserver: HTTPServer) -> HTTPServer:
    """Set up mock OpenAI server for integration tests."""

    def chat_completion_handler(request: Request) -> Response:
        """Handle chat completion requests with or without tools."""
        body = json.loads(request.data.decode("utf-8"))
        if "tools" in body and body.get("tool_choice"):
            response_data = OPENAI_RESPONSES["tool_response"]
        else:
            response_data = OPENAI_RESPONSES["text_response"]

        return Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    # Mock endpoints
    httpserver.expect_request(
        "/v1/chat/completions",
        method="POST",
    ).respond_with_handler(chat_completion_handler)

    # Add the POST /v1/batches endpoint that the official client uses
    httpserver.expect_request("/v1/batches", method="POST").respond_with_json(
        {
            "id": "batch_123",
            "object": "batch",
            "status": "completed",
            "input_file_id": "file_123",
            "completion_window": "24h",
            "endpoint": "/v1/chat/completions",
            "created_at": 1234567890,
            "in_progress_at": 1234567891,
            "expires_at": 1234654290,
            "finalizing_at": 1234567892,
            "completed_at": 1234567893,
            "request_counts": {"total": 100, "completed": 95, "failed": 5},
            "metadata": {"test": "data"},
        }
    )

    # Add the POST /v1/batches/{batch_id}/cancel endpoint that the official client uses
    httpserver.expect_request(
        "/v1/batches/batch_123/cancel", method="POST"
    ).respond_with_json(
        {
            "id": "batch_123",
            "object": "batch",
            "status": "cancelled",
            "input_file_id": "file_123",
            "completion_window": "24h",
            "endpoint": "/v1/chat/completions",
            "created_at": 1234567890,
            "in_progress_at": 1234567891,
            "expires_at": 1234654290,
            "finalizing_at": None,
            "completed_at": 1234567893,
            "request_counts": {"total": 100, "completed": 50, "failed": 0},
            "metadata": {"test": "data"},
        }
    )

    # Add the GET /v1/batches endpoint that the official client uses
    httpserver.expect_request("/v1/batches", method="GET").respond_with_json(
        {
            "object": "list",
            "data": [
                {
                    "id": "batch_1",
                    "object": "batch",
                    "status": "completed",
                    "endpoint": "/v1/chat/completions",
                    "input_file_id": "file_1",
                    "completion_window": "24h",
                    "created_at": 1234567890,
                    "in_progress_at": 1234567891,
                    "completed_at": 1234567892,
                    "output_file_id": "output_1",
                    "error_file_id": None,
                    "request_counts": {"total": 100, "completed": 100, "failed": 0},
                    "metadata": None,
                },
                {
                    "id": "batch_2",
                    "object": "batch",
                    "status": "in_progress",
                    "endpoint": "/v1/chat/completions",
                    "input_file_id": "file_2",
                    "completion_window": "24h",
                    "created_at": 1234567891,
                    "in_progress_at": 1234567892,
                    "completed_at": None,
                    "output_file_id": None,
                    "error_file_id": None,
                    "request_counts": {"total": 50, "completed": 25, "failed": 0},
                    "metadata": None,
                },
            ],
            "has_more": False,
        }
    )

    # Add the GET /v1/batches/{batch_id} endpoint that the official client uses
    httpserver.expect_request("/v1/batches/batch_123", method="GET").respond_with_json(
        {
            "id": "batch_123",
            "object": "batch",
            "status": "completed",
            "input_file_id": "file_123",
            "completion_window": "24h",
            "endpoint": "/v1/chat/completions",
            "created_at": 1234567890,
            "in_progress_at": 1234567891,
            "expires_at": 1234654290,
            "finalizing_at": 1234567892,
            "completed_at": 1234567893,
            "request_counts": {"total": 100, "completed": 95, "failed": 5},
            "metadata": {"test": "data"},
        }
    )

    httpserver.expect_request("/v1/files", method="POST").respond_with_json(
        {
            "id": "file_123",
            "object": "file",
            "bytes": 1024,
            "created_at": 1234567890,
            "filename": "test.jsonl",
            "purpose": "batch",
        }
    )

    httpserver.expect_request(
        "/v1/files/file_123/content", method="GET"
    ).respond_with_data(
        b'{"custom_id": "1", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}}\n'
    )

    # Mock completed batch results endpoint
    httpserver.expect_request("/v1/batch/completed", method="GET").respond_with_json(
        {
            "id": "batch_123",
            "object": "batch",
            "status": "completed",
            "results": [
                {
                    "custom_id": "paper-001",
                    "response": {
                        "status_code": 200,
                        "body": {
                            "id": "chatcmpl-batch-1",
                            "object": "chat.completion",
                            "created": 1677652288,
                            "model": "gpt-4o-mini",
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {
                                        "role": "assistant",
                                        "content": "This is a completed batch result for paper-001.",
                                    },
                                    "finish_reason": "stop",
                                }
                            ],
                            "usage": {
                                "prompt_tokens": 30,
                                "completion_tokens": 15,
                                "total_tokens": 45,
                            },
                        },
                    },
                }
            ],
        }
    )

    return httpserver


@pytest.fixture
def mock_arxiv_server(httpserver: HTTPServer) -> HTTPServer:
    """Set up mock arXiv server for integration tests."""

    def arxiv_query_handler(request: Request) -> Response:
        """Handle arXiv API query requests."""
        # Parse query parameters
        parsed_url = urlparse(request.url)
        query_params = parse_qs(parsed_url.query)
        id_list = query_params.get("id_list", [""])[0]
        search_query = query_params.get("search_query", [""])[0]

        # Handle any cs.AI category search with date range
        if "cat:cs.AI" in search_query and "submittedDate:" in search_query:
            # Return the example XML response for any cs.AI category search
            example_path = Path("tests", "assets", "example_arxiv_response.xml")
            with open(example_path, encoding="utf-8") as f:
                response_data = f.read()
            return Response(
                response_data,
                status=200,
                headers={"Content-Type": "application/xml"},
            )

        # Handle different paper scenarios for individual paper queries
        if id_list == "1706.99999":
            # Server error scenario
            return Response(
                "Internal Server Error",
                status=500,
                headers={"Content-Type": "text/plain"},
            )
        elif id_list in ARXIV_RESPONSES:
            response_data = ARXIV_RESPONSES[id_list]
        else:
            # Default response for other papers
            response_data = ARXIV_RESPONSES["default"]

        return Response(
            response_data,
            status=200,
            headers={"Content-Type": "application/xml"},
        )

    # Mock arXiv API endpoint
    httpserver.expect_request(
        "/api/query",
        method="GET",
    ).respond_with_handler(arxiv_query_handler)

    return httpserver


@pytest.fixture(scope="function")
def mock_arxiv_extractor(mock_arxiv_server: HTTPServer) -> ArxivExtractor:
    """Provide a mock ArxivExtractor instance configured with mock server."""
    base_url = f"http://{mock_arxiv_server.host}:{mock_arxiv_server.port}/api/query"
    return ArxivExtractor(api_base_url=base_url)


@pytest.fixture(scope="function")
def mock_arxiv_source_explorer(mock_arxiv_server: HTTPServer) -> ArxivSourceExplorer:
    """Provide a mock ArxivSourceExplorer instance configured with mock server."""
    base_url = f"http://{mock_arxiv_server.host}:{mock_arxiv_server.port}/api/query"
    return ArxivSourceExplorer(api_base_url=base_url)


@pytest.fixture
def mock_db_engine(tmp_path: Path) -> Engine:
    """Create a real database engine for testing using a file-based database."""
    # Use a file-based SQLite database in tmp_path to avoid in-memory engine instance issues
    db_path = tmp_path / "test.db"
    database_url = f"sqlite:///{db_path}"

    # Create engine with the file-based URL
    from sqlalchemy import create_engine

    engine = create_engine(
        database_url,
        echo=False,
        connect_args={
            "check_same_thread": False,
            "timeout": 60.0,
        },
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
    )
    create_database_tables(engine)
    return engine


@pytest.fixture(scope="function")
def mock_db_session(mock_db_engine: Engine) -> Generator[Session, None, None]:
    with Session(mock_db_engine) as session:
        yield session


@pytest.fixture(scope="function")
def mock_openai_client(
    mock_openai_server: HTTPServer,
) -> UnifiedOpenAIClient:
    """Provide a mock UnifiedOpenAIClient instance."""

    base_url = f"http://{mock_openai_server.host}:{mock_openai_server.port}/v1"
    return UnifiedOpenAIClient(
        api_key="test-api-key",
        base_url=base_url,
        timeout=60.0,
        model="super-ai-model",
        use_tools=True,
    )


@pytest.fixture
def paper_repo(mock_db_session: Session) -> PaperRepository:
    """Create paper repository instance."""
    return PaperRepository(mock_db_session)


@pytest.fixture
def llm_batch_repo(mock_db_session: Session) -> LLMBatchRepository:
    """Create LLM batch repository instance."""
    return LLMBatchRepository(mock_db_session)


@pytest.fixture
def saved_paper(paper_repo: PaperRepository) -> Paper:
    """Create and save a test paper."""
    paper = Paper(
        arxiv_id="2508.01234",
        title="Test Paper Title",
        abstract="Test paper abstract",
        primary_category="cs.AI",
        categories="cs.AI,cs.LG",
        authors="Author One;Author Two",
        url_abs="https://arxiv.org/abs/2508.01234",
        url_pdf="https://arxiv.org/pdf/2508.01234",
        published_at="2023-08-01T00:00:00Z",
        summary_status=PaperSummaryStatus.DONE,
    )
    return paper_repo.create(paper)


@pytest.fixture
def summary_repo(mock_db_session: Session) -> SummaryRepository:
    """Create summary repository instance."""
    return SummaryRepository(mock_db_session)


@pytest.fixture
def saved_summary(summary_repo: SummaryRepository, saved_paper: Paper) -> Summary:
    """Create and save a test summary."""
    summary = Summary(
        summary_id=1,
        paper_id=saved_paper.paper_id,
        version="1.0",
        overview="Test overview",
        motivation="Test motivation",
        method="Test method",
        result="Test result",
        conclusion="Test conclusion",
        language="English",
        interests="AI,ML",
        relevance=8,
        model="gpt-4",
    )
    return summary_repo.create(summary)


@pytest.fixture
def user_repo(mock_db_session: Session) -> UserRepository:
    """Create user repository instance."""
    return UserRepository(mock_db_session)


@pytest.fixture
def saved_user(user_repo: UserRepository) -> User:
    """Create and save a test user."""
    user = User(
        email="test@example.com",
        display_name="Test User",
    )
    return user_repo.create(user)


@pytest.fixture
def user_star_repo(mock_db_session: Session) -> UserStarRepository:
    """Create user star repository instance."""
    return UserStarRepository(mock_db_session)


@pytest.fixture
def summary_read_repo(mock_db_session: Session) -> SummaryReadRepository:
    """Create summary read repository instance."""
    return SummaryReadRepository(mock_db_session)


@pytest.fixture
def saved_papers(paper_repo: PaperRepository) -> list[Paper]:
    """Create and save multiple test papers with different statuses."""
    papers = [
        Paper(
            arxiv_id="2201.00001",
            title="Test Paper 1",
            abstract="Test Abstract 1",
            authors="Author 1",
            primary_category="cs.AI",
            categories="cs.AI,cs.LG",
            url_abs="http://arxiv.org/abs/2201.00001",
            url_pdf="http://arxiv.org/pdf/2201.00001",
            published_at="2023-01-01",  # Oldest
            summary_status=PaperSummaryStatus.BATCHED,
        ),
        Paper(
            arxiv_id="2201.00002",
            title="Test Paper 2",
            abstract="Test Abstract 2",
            authors="Author 2",
            primary_category="cs.AI",
            categories="cs.AI,cs.LG",
            url_abs="http://arxiv.org/abs/2201.00002",
            url_pdf="http://arxiv.org/pdf/2201.00002",
            published_at="2023-01-03",  # Newest
            summary_status=PaperSummaryStatus.BATCHED,
        ),
        Paper(
            arxiv_id="2201.00003",
            title="Test Paper 3",
            abstract="",  # Empty abstract
            authors="Author 3",
            primary_category="cs.AI",
            categories="cs.AI,cs.LG",
            url_abs="http://arxiv.org/abs/2201.00003",
            url_pdf="http://arxiv.org/pdf/2201.00003",
            published_at="2023-01-02",  # Middle
            summary_status=PaperSummaryStatus.DONE,  # Already processed
        ),
    ]

    # Save papers to database
    saved_papers = []
    for paper in papers:
        saved_paper = paper_repo.create(paper)
        saved_papers.append(saved_paper)

    return saved_papers


@pytest.fixture
def mock_background_manager() -> BackgroundBatchManager:
    """Background batch manager instance."""
    from unittest.mock import MagicMock

    mock_summary_service = MagicMock(spec=PaperSummarizationService)
    return BackgroundBatchManager(
        summary_service=mock_summary_service,
        batch_enabled=True,
        batch_summary_interval=3600,
        batch_fetch_interval=600,
        batch_max_items=1000,
        language="English",
    )


@pytest.fixture
def sample_arxiv_paper() -> ArxivPaper:
    """Create a sample ArxivPaper for testing based on mock response."""
    return ArxivPaper(
        arxiv_id="2501.00961v3",
        title="Uncovering Memorization Effect in the Presence of Spurious Correlations",
        abstract="Machine learning models often rely on simple spurious features -- patterns in training data that correlate with targets but are not causally related to them, like image backgrounds in foreground classification. This reliance typically leads to imbalanced test performance across minority and majority groups.",
        primary_category="cs.LG",
        categories=["cs.LG", "cs.AI", "cs.CV", "eess.IV"],
        authors=[
            "Chenyu You",
            "Haocheng Dai",
            "Yifei Min",
            "Jasjeet S. Sekhon",
            "Sarang Joshi",
            "James S. Duncan",
        ],
        url_abs="https://arxiv.org/abs/2501.00961v3",
        url_pdf="https://arxiv.org/pdf/2501.00961v3",
        published_date="2025-01-01T21:45:00Z",
        updated_date="2025-01-01T21:45:00Z",
        doi=None,
        journal=None,
        volume=None,
        pages=None,
    )


@pytest.fixture
def sample_batches() -> list[dict[str, Any]]:
    """Sample batch requests for testing."""
    return [
        {
            "batch_id": "batch_123",
            "status": "in_progress",
            "input_file_id": "file_123",
            "output_file_id": None,
            "created_at": "2024-01-01T10:00:00Z",
            "in_progress_at": "2024-01-01T10:05:00Z",
        },
        {
            "batch_id": "batch_456",
            "status": "validating",
            "input_file_id": "file_456",
            "output_file_id": None,
            "created_at": "2024-01-01T11:00:00Z",
            "in_progress_at": None,
        },
    ]
