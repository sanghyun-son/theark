"""Unit tests for SummaryGenerator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.llm.applications.summary import SummaryGenerator
from core.llm.openai_client import UnifiedOpenAIClient
from core.models.external.openai import (
    ChatCompletionResponse,
    OpenAIMessage,
    OpenAITool,
    OpenAIToolChoice,
    PaperAnalysis,
)


@pytest.fixture
def mock_llm_client():
    """Create a mock UnifiedOpenAIClient."""
    client = AsyncMock()
    client.model = "gpt-4o-mini"
    client.use_tools = True

    # Mock the internal _client
    mock_internal_client = AsyncMock()
    mock_chat_completions = AsyncMock()
    mock_internal_client.chat.completions = mock_chat_completions
    client._client = mock_internal_client

    return client


@pytest.fixture
def summary_generator():
    """Create a SummaryGenerator."""
    return SummaryGenerator()


@pytest.fixture
def sample_content():
    """Sample paper content for testing."""
    return "This paper presents a novel approach to machine learning."


@pytest.fixture
def sample_interest_section():
    """Sample interest section for testing."""
    return "Machine Learning, AI, Computer Science"


def test_summary_generator_initialization():
    """Test SummaryGenerator initialization."""
    generator = SummaryGenerator()
    assert generator is not None


def test_create_summarization_messages(
    summary_generator, sample_content, sample_interest_section
):
    """Test _create_summarization_messages method."""
    messages = summary_generator._create_summarization_messages(
        sample_content, sample_interest_section, "English"
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "English" in messages[0].content
    assert sample_content in messages[1].content
    assert sample_interest_section in messages[1].content


def test_create_summarization_messages_korean(
    summary_generator, sample_content, sample_interest_section
):
    """Test _create_summarization_messages with Korean language."""
    messages = summary_generator._create_summarization_messages(
        sample_content, sample_interest_section, "Korean"
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "Korean" in messages[0].content
    assert sample_content in messages[1].content
    assert sample_interest_section in messages[1].content


def test_create_paper_analysis_tool(summary_generator):
    """Test _create_paper_analysis_tool method."""
    tool = summary_generator._create_paper_analysis_tool("English")

    assert isinstance(tool, OpenAITool)
    assert tool.function.name == "Structure"
    assert (
        tool.function.description
        == "Analyze paper abstract and extract key information"
    )


def test_create_tool_choice(summary_generator):
    """Test _create_tool_choice method."""
    tool_choice = summary_generator._create_tool_choice()

    assert isinstance(tool_choice, OpenAIToolChoice)
    assert tool_choice.function == {"name": "Structure"}


@pytest.mark.asyncio
async def test_summarize_paper_success(
    summary_generator, mock_llm_client, sample_content, sample_interest_section
):
    """Test successful paper summarization."""
    # Mock response
    mock_response = ChatCompletionResponse(
        id="test-id",
        object="chat.completion",
        created=1234567890,
        model="gpt-4o-mini",
        choices=[],
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )

    mock_llm_client._client.chat.completions.create.return_value = mock_response

    # Call the method
    result = await summary_generator.summarize_paper(
        mock_llm_client,
        content=sample_content,
        interest_section=sample_interest_section,
        language="English",
    )

    # Verify the result
    assert result == mock_response

    # Verify the client was called correctly
    mock_llm_client._client.chat.completions.create.assert_called_once()
    call_args = mock_llm_client._client.chat.completions.create.call_args
    request_data = call_args[1]  # Keyword arguments

    # Verify the request data
    assert request_data["model"] == "gpt-4o-mini"
    assert len(request_data["messages"]) == 2
    assert request_data["messages"][0]["role"] == "system"
    assert request_data["messages"][1]["role"] == "user"
    assert sample_content in request_data["messages"][1]["content"]
    assert sample_interest_section in request_data["messages"][1]["content"]


@pytest.mark.asyncio
async def test_summarize_paper_with_custom_model(
    summary_generator, mock_llm_client, sample_content, sample_interest_section
):
    """Test paper summarization with custom model."""
    mock_response = ChatCompletionResponse(
        id="test-id",
        object="chat.completion",
        created=1234567890,
        model="gpt-4",
        choices=[],
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )

    mock_llm_client._client.chat.completions.create.return_value = mock_response

    # Call with custom model
    await summary_generator.summarize_paper(
        mock_llm_client,
        content=sample_content,
        interest_section=sample_interest_section,
        model="gpt-4",
        use_tools=False,
    )

    # Verify custom parameters were passed
    call_args = mock_llm_client._client.chat.completions.create.call_args
    request_data = call_args[1]  # Keyword arguments
    assert request_data["model"] == "gpt-4"  # model parameter
    assert request_data["tools"] is None  # use_tools=False means no tools


@pytest.mark.asyncio
async def test_summarize_paper_with_tracking(
    summary_generator, mock_llm_client, sample_content, sample_interest_section
):
    """Test paper summarization with database tracking."""
    mock_response = ChatCompletionResponse(
        id="test-id",
        object="chat.completion",
        created=1234567890,
        model="gpt-4o-mini",
        choices=[],
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )

    mock_llm_client._client.chat.completions.create.return_value = mock_response

    mock_db_manager = MagicMock()

    # Call with tracking parameters
    await summary_generator.summarize_paper(
        mock_llm_client,
        content=sample_content,
        interest_section=sample_interest_section,
        db_manager=mock_db_manager,
        custom_id="test-paper-123",
    )

    # Verify the request was made (tracking is handled internally)
    mock_llm_client._client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_summarize_paper_client_error(
    summary_generator, mock_llm_client, sample_content, sample_interest_section
):
    """Test paper summarization when client raises an error."""
    mock_llm_client._client.chat.completions.create.side_effect = Exception("API Error")

    # Should propagate the error
    with pytest.raises(Exception, match="API Error"):
        await summary_generator.summarize_paper(
            mock_llm_client,
            content=sample_content,
            interest_section=sample_interest_section,
        )
