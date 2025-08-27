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

from core.llm.openai_client import UnifiedOpenAIClient
from core.database.interfaces import DatabaseManager
from core.extractors.concrete.arxiv_extractor import ArxivExtractor
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

    # Add a specific response for batch creation without metadata
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
            "metadata": None,
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
