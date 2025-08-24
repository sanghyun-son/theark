"""Global pytest configuration and fixtures."""

import json

import pytest
import pytest_asyncio
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

from core import setup_test_logging
from tests.shared_test_data import ARXIV_RESPONSES, OPENAI_RESPONSES


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Setup test logging for all tests."""
    setup_test_logging()


@pytest.fixture(scope="function")
def logger():
    """Provide a logger instance for tests."""
    from core import get_logger

    return get_logger("test")


@pytest_asyncio.fixture
async def mock_openai_server(httpserver: HTTPServer) -> HTTPServer:
    """Set up mock OpenAI server for integration tests."""

    def chat_completion_handler(request):
        """Handle chat completion requests with or without tools."""
        body = json.loads(request.data.decode("utf-8"))

        # Check if tools are used
        if "tools" in body and body.get("tool_choice"):
            response_data = OPENAI_RESPONSES["tool_response"]
        else:
            response_data = OPENAI_RESPONSES["text_response"]

        return Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    def batch_handler(request):
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
        headers={"Authorization": "Bearer test-api-key"},
    ).respond_with_handler(chat_completion_handler)

    httpserver.expect_request(
        "/v1/batch",
        method="POST",
        headers={"Authorization": "Bearer test-api-key"},
    ).respond_with_handler(batch_handler)

    return httpserver


@pytest_asyncio.fixture
async def mock_arxiv_server(httpserver: HTTPServer) -> HTTPServer:
    """Set up mock arXiv server for integration tests."""

    def arxiv_query_handler(request):
        """Handle arXiv API query requests."""
        from urllib.parse import parse_qs, urlparse

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
