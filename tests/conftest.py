"""Global pytest configuration and fixtures."""

import json
from logging import Logger
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Request, Response

from core import setup_test_logging

from core.database.interfaces import DatabaseManager
from core.extractors.concrete.arxiv_extractor import ArxivExtractor
from crawler.summarizer.openai_summarizer import OpenAISummarizer
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

    def batch_handler(request: Request) -> Response:
        """Handle batch requests for multiple summaries."""
        return Response(
            json.dumps(OPENAI_RESPONSES["batch_response"]),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    # Mock endpoints
    httpserver.expect_request(
        "/v1/chat/completions",
        method="POST",
    ).respond_with_handler(chat_completion_handler)

    httpserver.expect_request(
        "/v1/batch",
        method="POST",
    ).respond_with_handler(batch_handler)

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

        # Handle different paper scenarios
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


@pytest_asyncio.fixture(scope="function")
async def mock_db_manager(tmp_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    """Provide a real SQLite database manager for tests using temporary path."""
    from core.database.implementations.sqlite import SQLiteManager

    db_path = tmp_path / "test.db"
    db_manager: DatabaseManager = SQLiteManager(db_path)
    async with db_manager:
        await db_manager.create_tables()
        yield db_manager


@pytest.fixture(scope="function")
def mock_summary_client(
    mock_openai_server: HTTPServer,
) -> OpenAISummarizer:
    """Provide a mock OpenAISummarizer instance."""

    base_url = f"http://{mock_openai_server.host}:{mock_openai_server.port}/v1"
    return OpenAISummarizer(
        api_key="test-api-key",
        base_url=base_url,
        timeout=60.0,
        model="super-ai-model",
        use_tools=True,
    )
