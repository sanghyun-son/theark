"""Global pytest configuration and fixtures."""

import json
from collections.abc import Generator
from logging import Logger
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from pytest_httpserver import HTTPServer
from sqlalchemy import create_engine
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

from tests.utils.test_helpers import TestDataFactory


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

    example_path = Path("tests", "assets", "openai_responses.json")
    with open(example_path, "r") as f:
        openai_responses = json.load(f)

    def chat_completion_handler(request: Request) -> Response:
        """Handle chat completion requests with or without tools."""
        body = json.loads(request.data.decode("utf-8"))
        if "tools" in body and body.get("tool_choice"):
            response_data = openai_responses["tool_response"]
        else:
            response_data = openai_responses["text_response"]

        return Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    # Mock Chat Completions endpoint
    httpserver.expect_request(
        "/v1/chat/completions",
        method="POST",
    ).respond_with_handler(chat_completion_handler)

    httpserver.expect_request("/v1/batches", method="POST").respond_with_json(
        openai_responses["create_batch"]
    )
    httpserver.expect_request("/v1/batches", method="GET").respond_with_json(
        openai_responses["list_batches"]
    )
    httpserver.expect_request("/v1/batches/batch_123", method="GET").respond_with_json(
        openai_responses["get_batch_status"]
    )
    httpserver.expect_request(
        "/v1/batches/batch_123/cancel", method="POST"
    ).respond_with_json(openai_responses["cancel_batch"])
    httpserver.expect_request(
        "/v1/batches/batch_123/output", method="GET"
    ).respond_with_json(openai_responses["get_batch_output"])
    httpserver.expect_request("/v1/files", method="POST").respond_with_json(
        openai_responses["upload_file"]
    )
    httpserver.expect_request("/v1/files", method="GET").respond_with_json(
        openai_responses["list_files"]
    )
    httpserver.expect_request("/v1/files/file_123", method="GET").respond_with_json(
        openai_responses["get_file_info"]
    )
    httpserver.expect_request(
        "/v1/files/file_123/content", method="GET"
    ).respond_with_data(
        b'{"custom_id": "1", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}}\n'
    )
    httpserver.expect_request("/v1/files/file_123", method="DELETE").respond_with_json(
        openai_responses["delete_file"]
    )

    return httpserver


@pytest.fixture
def mock_arxiv_server(httpserver: HTTPServer) -> HTTPServer:
    """Set up mock arXiv server for integration tests."""

    # Load ArXiv responses from JSON file
    arxiv_responses_path = Path("tests", "assets", "arxiv_responses.json")
    with open(arxiv_responses_path, "r") as f:
        arxiv_responses = json.load(f)

    def create_subset_xml_response(
        xml_content: str, start: int, max_results: int
    ) -> str:
        """Create a subset XML response based on start and max_results parameters."""
        import xml.etree.ElementTree as ElementTree

        root = ElementTree.fromstring(xml_content)

        # Try to find entries with and without namespace
        entries = root.findall("entry")
        if not entries:
            # Try with namespace
            entries = root.findall(".//entry")
        if not entries:
            # Try with explicit namespace
            entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        total_papers = len(entries)
        start_index = min(start, total_papers)
        end_index = min(start + max_results, total_papers)

        print(
            f"DEBUG: total_papers={total_papers}, start={start}, max_results={max_results}"
        )
        print(f"DEBUG: start_index={start_index}, end_index={end_index}")
        print(f"DEBUG: papers to return: {end_index - start_index}")

        new_root = ElementTree.Element("feed")
        new_root.set("xmlns", "http://www.w3.org/2005/Atom")

        # Copy feed metadata (title, id, updated, etc.) - but NOT entries
        for child in root:
            if not child.tag.endswith("entry"):  # entry로 끝나지 않는 요소만 복사
                new_root.append(child)

        # Add ONLY the subset of entries based on start and max_results
        for i in range(start_index, end_index):
            if i < len(entries):
                new_root.append(entries[i])

        # Convert back to string
        result = ElementTree.tostring(new_root, encoding="unicode")
        print(f"DEBUG: Final XML length: {len(result)}")
        return result

    def arxiv_query_handler(request: Request) -> Response:
        """Handle arXiv API query requests."""
        # Parse query parameters
        parsed_url = urlparse(request.url)
        query_params = parse_qs(parsed_url.query)
        id_list = query_params.get("id_list", [""])[0]
        search_query = query_params.get("search_query", [""])[0]
        max_results = int(query_params.get("max_results", ["10"])[0])
        start = int(query_params.get("start", ["0"])[0])

        if "cat:cs.AI" in search_query:
            # Load the example XML and return subset based on start and max_results
            example_path = Path(
                "tests",
                "assets",
                "example_arxiv_range_query_response.xml",
            )
            with open(example_path, encoding="utf-8") as f:
                xml_content = f.read()

            # Create subset XML response
            response_data = create_subset_xml_response(xml_content, start, max_results)
            return Response(
                response_data,
                status=200,
                headers={"Content-Type": "application/xml"},
            )

        # Handle non-existent categories with empty response
        if "cat:nonexistent" in search_query:
            empty_feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>ArXiv Query Results</title>
    <id>http://arxiv.org/api/query?search_query=cat:nonexistent</id>
    <updated>2024-01-01T00:00:00Z</updated>
    <opensearch:totalResults>0</opensearch:totalResults>
    <opensearch:startIndex>0</opensearch:startIndex>
    <opensearch:itemsPerPage>10</opensearch:itemsPerPage>
</feed>"""
            return Response(
                empty_feed,
                status=200,
                headers={"Content-Type": "application/xml"},
            )

        if id_list == "1706.99999":
            # Server error scenario
            return Response(
                "Internal Server Error",
                status=500,
                headers={"Content-Type": "text/plain"},
            )
        elif id_list in arxiv_responses:
            response_data = arxiv_responses[id_list]
        else:
            # Default response for other papers
            response_data = arxiv_responses["default"]

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
def mock_db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    """Create a real database engine for testing using a file-based database."""
    # Use a file-based SQLite database in tmp_path to avoid in-memory engine instance issues
    db_path = tmp_path / "test.db"
    database_url = f"sqlite:///{db_path}"

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
    yield engine
    engine.dispose()


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
    paper = TestDataFactory.create_test_paper()
    return paper_repo.create(paper)


@pytest.fixture
def summary_repo(mock_db_session: Session) -> SummaryRepository:
    """Create summary repository instance."""
    return SummaryRepository(mock_db_session)


@pytest.fixture
def saved_summary(summary_repo: SummaryRepository, saved_paper: Paper) -> Summary:
    """Create and save a test summary."""
    assert saved_paper.paper_id is not None
    summary = TestDataFactory.create_test_summary(saved_paper.paper_id)
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
        batch_summary_interval=3600,
        batch_fetch_interval=600,
        batch_max_items=1000,
        batch_daily_limit=5,
        language="English",
        interests=["Machine Learning"],
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
