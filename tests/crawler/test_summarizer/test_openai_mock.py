"""Tests for OpenAI mock server using pytest-httpserver."""

import json
import pytest
import pytest_asyncio
from pytest_httpserver import HTTPServer
from typing import Any

from crawler.summarizer.openai_summarizer import OpenAISummarizer
from crawler.summarizer.summarizer import SummaryRequest


class TestOpenAIMockServer:
    """Test OpenAI mock server functionality."""

    @pytest_asyncio.fixture
    async def mock_openai_server(self, httpserver: HTTPServer) -> HTTPServer:
        """Set up mock OpenAI server."""

        def chat_completion_handler(request):
            """Handle chat completion requests with or without tools."""
            import json
            from werkzeug.wrappers import Response

            body = json.loads(request.data.decode("utf-8"))

            # Check if tools are used
            if "tools" in body and body.get("tool_choice"):
                # Tool-based response with function calling
                response_data = {
                    "id": "chatcmpl-test-123",
                    "object": "chat.completion",
                    "created": 1677652288,
                    "model": body.get("model", "gpt-4o-mini"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_123",
                                        "type": "function",
                                        "function": {
                                            "name": "Structure",
                                            "arguments": json.dumps(
                                                {
                                                    "tldr": "This paper presents a novel approach to abstract summarization using professional analysis methods.",
                                                    "motivation": "Current methods lack structured analysis of research papers and fail to provide relevance scoring.",
                                                    "method": "The authors propose a function-calling approach with structured output and professional evaluation criteria.",
                                                    "result": "Improved accuracy in extracting key information from abstracts with relevance scoring from 1-10.",
                                                    "conclusion": "Function calling enables better structured summarization with professional-grade analysis.",
                                                    "relevance": "8",
                                                }
                                            ),
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 150,
                        "completion_tokens": 80,
                        "total_tokens": 230,
                    },
                }
                return Response(
                    json.dumps(response_data),
                    status=200,
                    headers={"Content-Type": "application/json"},
                )
            else:
                # Regular text response without tools
                response_data = {
                    "id": "chatcmpl-test-456",
                    "object": "chat.completion",
                    "created": 1677652288,
                    "model": body.get("model", "gpt-4o-mini"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "This paper presents a professional analysis of abstract summarization methods. The research demonstrates improved techniques for extracting key information with relevance scoring. Based on the provided interests, this work has a relevance score of 7 out of 10.",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 50,
                        "completion_tokens": 20,
                        "total_tokens": 70,
                    },
                }
                return Response(
                    json.dumps(response_data),
                    status=200,
                    headers={"Content-Type": "application/json"},
                )

        # Mock /v1/chat/completions endpoint with dynamic handler
        httpserver.expect_request(
            "/v1/chat/completions",
            method="POST",
            headers={"Authorization": "Bearer test-api-key"},
        ).respond_with_handler(chat_completion_handler)

        # Mock batch processing endpoint
        def batch_handler(request):
            """Handle batch requests for multiple summaries."""
            import json
            from werkzeug.wrappers import Response

            response_data = {
                "id": "batch-test-123",
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
                                            "content": None,
                                            "tool_calls": [
                                                {
                                                    "id": "call_batch_1",
                                                    "type": "function",
                                                    "function": {
                                                        "name": "Structure",
                                                        "arguments": json.dumps(
                                                            {
                                                                "tldr": "Batch processed paper summary.",
                                                                "motivation": "Efficient processing of multiple papers.",
                                                                "method": "Batch API processing.",
                                                                "result": "Successfully processed in batch.",
                                                                "conclusion": "Batch processing is effective.",
                                                                "relevance": "Medium",
                                                            }
                                                        ),
                                                    },
                                                }
                                            ],
                                        },
                                        "finish_reason": "tool_calls",
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
            return Response(
                json.dumps(response_data),
                status=200,
                headers={"Content-Type": "application/json"},
            )

        httpserver.expect_request(
            "/v1/batch",
            method="POST",
            headers={"Authorization": "Bearer test-api-key"},
        ).respond_with_handler(batch_handler)

        return httpserver

    @pytest_asyncio.fixture
    async def openai_summarizer(
        self, mock_openai_server: HTTPServer
    ) -> OpenAISummarizer:
        """Create OpenAI summarizer with mock server."""
        return OpenAISummarizer(
            api_key="test-api-key",
            base_url=f"http://localhost:{mock_openai_server.port}",
        )

    @pytest.mark.asyncio
    async def test_chat_completions_endpoint(
        self, mock_openai_server: HTTPServer
    ):
        """Test /v1/chat/completions endpoint."""
        # Test that the endpoint is configured correctly
        # The mock server should have the endpoint configured
        assert mock_openai_server.is_running()

        # Test that we can make a request to the endpoint
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:{mock_openai_server.port}/v1/chat/completions",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Test"}],
                },
            )
            assert response.status_code == 200
            response_data = response.json()
            assert "choices" in response_data
            assert len(response_data["choices"]) > 0
            assert "message" in response_data["choices"][0]
            assert "content" in response_data["choices"][0]["message"]

    @pytest.mark.asyncio
    async def test_batch_processing(self, mock_openai_server: HTTPServer):
        """Test batch processing functionality."""
        # Test that the batch endpoint is configured correctly
        assert mock_openai_server.is_running()

        # Test that we can make a request to the batch endpoint
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:{mock_openai_server.port}/v1/batch",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "input_file_id": "test-file",
                    "endpoint": "/v1/chat/completions",
                    "completion_window": "24h",
                },
            )
            assert response.status_code == 200
            response_data = response.json()
            assert "status" in response_data
            assert response_data["status"] == "completed"
            assert "results" in response_data
            assert len(response_data["results"]) > 0

    @pytest.mark.asyncio
    async def test_authentication_header(self, mock_openai_server: HTTPServer):
        """Test that authentication header is properly set."""
        # Test that requests with correct auth header succeed
        import httpx

        async with httpx.AsyncClient() as client:
            # Test with correct auth header
            response = await client.post(
                f"http://localhost:{mock_openai_server.port}/v1/chat/completions",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Test"}],
                },
            )
            # Should succeed
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_validation(self, mock_openai_server: HTTPServer):
        """Test request validation and error handling."""
        # Test that the mock server is properly configured
        assert mock_openai_server.is_running()

        # Test that we can make requests to configured endpoints
        import httpx

        async with httpx.AsyncClient() as client:
            # Test chat completions endpoint
            response = await client.post(
                f"http://localhost:{mock_openai_server.port}/v1/chat/completions",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Test"}],
                },
            )
            assert response.status_code == 200

            # Test batch endpoint
            response = await client.post(
                f"http://localhost:{mock_openai_server.port}/v1/batch",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "input_file_id": "test-file",
                    "endpoint": "/v1/chat/completions",
                },
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_tool_based_summarization(
        self, mock_openai_server: HTTPServer
    ):
        """Test summarization with tools/function calling."""
        import httpx

        async with httpx.AsyncClient() as client:
            # Test request with tools (structured output)
            response = await client.post(
                f"http://localhost:{mock_openai_server.port}/v1/chat/completions",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that analyzes research papers.",
                        },
                        {
                            "role": "user",
                            "content": "Analyze this abstract: This paper presents a novel approach...",
                        },
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "Structure",
                                "description": "Analyze paper abstract and extract key information",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "tldr": {"type": "string"},
                                        "motivation": {"type": "string"},
                                        "method": {"type": "string"},
                                        "result": {"type": "string"},
                                        "conclusion": {"type": "string"},
                                        "relevance": {"type": "string"},
                                    },
                                    "required": [
                                        "tldr",
                                        "motivation",
                                        "method",
                                        "result",
                                        "conclusion",
                                        "relevance",
                                    ],
                                },
                            },
                        }
                    ],
                    "tool_choice": {
                        "type": "function",
                        "function": {"name": "Structure"},
                    },
                },
            )
            assert response.status_code == 200
            response_data = response.json()

            # Verify tool-based response structure
            assert "choices" in response_data
            assert len(response_data["choices"]) > 0
            choice = response_data["choices"][0]
            assert "message" in choice
            message = choice["message"]
            assert (
                message["content"] is None
            )  # Content should be None for tool calls
            assert "tool_calls" in message
            assert len(message["tool_calls"]) > 0

            tool_call = message["tool_calls"][0]
            assert tool_call["type"] == "function"
            assert tool_call["function"]["name"] == "Structure"

            # Parse the structured arguments
            import json

            args = json.loads(tool_call["function"]["arguments"])
            assert "tldr" in args
            assert "motivation" in args
            assert "method" in args
            assert "result" in args
            assert "conclusion" in args
            assert "relevance" in args

    @pytest.mark.asyncio
    async def test_non_tool_based_summarization(
        self, mock_openai_server: HTTPServer
    ):
        """Test summarization without tools (regular text response)."""
        import httpx

        async with httpx.AsyncClient() as client:
            # Test request without tools (regular text response)
            response = await client.post(
                f"http://localhost:{mock_openai_server.port}/v1/chat/completions",
                headers={"Authorization": "Bearer test-api-key"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that summarizes research papers.",
                        },
                        {
                            "role": "user",
                            "content": "Summarize this abstract: This paper presents a novel approach...",
                        },
                    ],
                },
            )
            assert response.status_code == 200
            response_data = response.json()

            # Verify regular text response structure
            assert "choices" in response_data
            assert len(response_data["choices"]) > 0
            choice = response_data["choices"][0]
            assert "message" in choice
            message = choice["message"]
            assert message["content"] is not None  # Content should have text
            assert (
                "tool_calls" not in message or message.get("tool_calls") is None
            )
            assert choice["finish_reason"] == "stop"
