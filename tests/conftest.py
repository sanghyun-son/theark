"""Global pytest configuration and fixtures."""

import json

import pytest
import pytest_asyncio
from pytest_httpserver import HTTPServer

from core import setup_test_logging


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
        from werkzeug.wrappers import Response

        body = json.loads(request.data.decode("utf-8"))

        # Common response structure
        base_response = {
            "id": "chatcmpl-test-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": body.get("model", "gpt-4o-mini"),
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 80,
                "total_tokens": 230,
            },
        }

        # Check if tools are used
        if "tools" in body and body.get("tool_choice"):
            # Tool-based response with function calling
            structured_data = {
                "tldr": "This paper presents a novel approach to abstract summarization using professional analysis methods.",
                "motivation": "Current methods lack structured analysis of research papers and fail to provide relevance scoring.",
                "method": "The authors propose a function-calling approach with structured output and professional evaluation criteria.",
                "result": "Improved accuracy in extracting key information from abstracts with relevance scoring from 1-10.",
                "conclusion": "Function calling enables better structured summarization with professional-grade analysis.",
                "relevance": "8",
            }

            response_data = {
                **base_response,
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
                                        "arguments": json.dumps(structured_data),
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }
        else:
            # Regular text response without tools
            response_data = {
                **base_response,
                "id": "chatcmpl-test-456",
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 20,
                    "total_tokens": 70,
                },
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
        from werkzeug.wrappers import Response

        batch_structured_data = {
            "tldr": "Batch processed paper summary.",
            "motivation": "Efficient processing of multiple papers.",
            "method": "Batch API processing.",
            "result": "Successfully processed in batch.",
            "conclusion": "Batch processing is effective.",
            "relevance": "Medium",
        }

        batch_choice = {
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
                            "arguments": json.dumps(batch_structured_data),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }

        batch_completion = {
            "id": "chatcmpl-batch-1",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4o-mini",
            "choices": [batch_choice],
            "usage": {
                "prompt_tokens": 30,
                "completion_tokens": 15,
                "total_tokens": 45,
            },
        }

        response_data = {
            "id": "batch-test-123",
            "object": "batch",
            "status": "completed",
            "results": [
                {
                    "custom_id": "paper-001",
                    "response": {
                        "status_code": 200,
                        "body": batch_completion,
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
async def mock_arxiv_server(httpserver: HTTPServer) -> HTTPServer:
    """Set up mock arXiv server for integration tests."""

    def arxiv_query_handler(request):
        """Handle arXiv API query requests."""
        from werkzeug.wrappers import Response
        from urllib.parse import parse_qs, urlparse

        # Parse query parameters
        parsed_url = urlparse(request.url)
        query_params = parse_qs(parsed_url.query)
        id_list = query_params.get("id_list", [""])[0]

        # Handle different paper scenarios
        if id_list == "1706.03762":
            # Attention Is All You Need paper
            response_data = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762</id>
    <updated>2017-12-06T00:37:27Z</updated>
    <published>2017-06-12T17:57:58Z</published>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent or
convolutional neural networks that include an encoder and a decoder. The best
performing models also connect the encoder and decoder through an attention
mechanism. We propose a new simple network architecture, the Transformer,
based solely on attention mechanisms, dispensing with recurrence and
convolutions entirely.</summary>
    <author>
      <name>Ashish Vaswani</name>
    </author>
    <author>
      <name>Noam Shazeer</name>
    </author>
    <author>
      <name>Niki Parmar</name>
    </author>
    <link href="http://arxiv.org/abs/1706.03762" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762" rel="related" type="application/pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""
        elif id_list == "9999.99999":
            # Paper not found
            response_data = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:totalResults>
  <opensearch:startIndex xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:startIndex>
  <opensearch:itemsPerPage xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:itemsPerPage>
</feed>"""
        elif id_list == "1706.99999":
            # Server error scenario
            return Response(
                "Internal Server Error",
                status=500,
                headers={"Content-Type": "text/plain"},
            )
        else:
            # Default response (ImageNet paper for 1409.0575 and others)
            authors = [
                "Olga Russakovsky",
                "Jia Deng",
                "Hao Su",
                "Jonathan Krause",
                "Sanjeev Satheesh",
                "Sean Ma",
                "Zhiheng Huang",
                "Andrej Karpathy",
                "Aditya Khosla",
                "Michael Bernstein",
                "Alexander C. Berg",
                "Li Fei-Fei",
            ]

            author_elements = "".join(
                [
                    f"    <author>\n      <name>{author}</name>\n    </author>\n"
                    for author in authors
                ]
            )

            response_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1409.0575</id>
    <updated>2014-09-01T22:29:38Z</updated>
    <published>2014-09-01T22:29:38Z</published>
    <title>ImageNet Large Scale Visual Recognition Challenge</title>
    <summary>The ImageNet Large Scale Visual Recognition Challenge is a benchmark in
object category classification and detection on hundreds of object categories
and millions of images. The challenge has been run annually from 2010 to
present, attracting participation from more than fifty institutions.
  This paper describes the creation of this benchmark dataset and the advances
in object recognition that have been possible as a result. We discuss the
challenges of collecting large-scale ground truth annotation, highlight key
breakthroughs in categorical object recognition, provide a detailed analysis of
the current state of the field of large-scale image classification and object
detection, and compare the state-of-the-art computer vision accuracy with human
accuracy. We conclude with lessons learned in the five years of the challenge,
and propose future directions and improvements.</summary>
{author_elements}    <link href="http://arxiv.org/abs/1409.0575" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1409.0575" rel="related" type="application/pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
    <category term="I.4.8; I.5.2" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""

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
