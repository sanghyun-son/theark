"""Integration tests for SummaryGenerator using mock OpenAI server."""

import pytest

from core.llm.applications.summary import SummaryGenerator
from core.llm.openai_client import UnifiedOpenAIClient
from core.models.external.openai import ChatCompletionResponse


@pytest.fixture
def openai_client(mock_openai_server):
    """Create OpenAI client pointing to mock server."""
    return UnifiedOpenAIClient(
        api_key="test-key",
        base_url=mock_openai_server.url_for("/v1"),
        timeout=10.0,
    )


@pytest.fixture
def summary_generator():
    """Create SummaryGenerator."""
    return SummaryGenerator()


@pytest.fixture
def sample_paper_content():
    """Sample paper abstract content."""
    return """
    This paper introduces a novel deep learning architecture for natural language processing.
    The proposed model achieves state-of-the-art performance on multiple benchmark datasets
    while requiring significantly less computational resources than existing approaches.
    We demonstrate the effectiveness of our method through extensive experiments and ablation studies.
    """


@pytest.fixture
def sample_interest_section():
    """Sample interest section."""
    return "Deep Learning, Natural Language Processing, Machine Learning"


@pytest.mark.asyncio
async def test_summary_generator_with_mock_server(
    summary_generator, openai_client, sample_paper_content, sample_interest_section
):
    """Test SummaryGenerator with mock OpenAI server."""
    # Call the summary generator
    response = await summary_generator.summarize_paper(
        openai_client,
        content=sample_paper_content,
        interest_section=sample_interest_section,
        language="English",
    )

    # Verify response structure
    assert isinstance(response, ChatCompletionResponse)
    assert response.id is not None
    assert response.model is not None
    assert response.choices is not None
    assert response.usage is not None


@pytest.mark.asyncio
async def test_summary_generator_korean_language(
    summary_generator, openai_client, sample_paper_content, sample_interest_section
):
    """Test SummaryGenerator with Korean language."""
    response = await summary_generator.summarize_paper(
        openai_client,
        content=sample_paper_content,
        interest_section=sample_interest_section,
        language="Korean",
    )

    # Verify response structure
    assert isinstance(response, ChatCompletionResponse)
    assert response.id is not None
    assert response.model is not None


@pytest.mark.asyncio
async def test_summary_generator_with_custom_model(
    summary_generator, openai_client, sample_paper_content, sample_interest_section
):
    """Test SummaryGenerator with custom model."""
    response = await summary_generator.summarize_paper(
        openai_client,
        content=sample_paper_content,
        interest_section=sample_interest_section,
        model="gpt-4",
        use_tools=False,
    )

    # Verify response structure
    assert isinstance(response, ChatCompletionResponse)
    assert response.id is not None
    assert response.model is not None


@pytest.mark.asyncio
async def test_summary_generator_message_structure(
    summary_generator, sample_paper_content, sample_interest_section
):
    """Test that SummaryGenerator creates correct message structure."""
    # Get the messages that would be sent
    messages = summary_generator._create_summarization_messages(
        sample_paper_content, sample_interest_section, "English"
    )

    # Verify message structure
    assert len(messages) == 2

    # System message
    system_msg = messages[0]
    assert system_msg.role == "system"
    assert "English" in system_msg.content

    # User message
    user_msg = messages[1]
    assert user_msg.role == "user"
    assert sample_paper_content in user_msg.content
    assert sample_interest_section in user_msg.content


@pytest.mark.asyncio
async def test_summary_generator_tool_creation(summary_generator):
    """Test that SummaryGenerator creates correct tools."""
    tool = summary_generator._create_paper_analysis_tool("English")

    # Verify tool structure
    assert tool.function.name == "Structure"
    assert (
        tool.function.description
        == "Analyze paper abstract and extract key information"
    )
    assert tool.function.parameters is not None

    # Verify tool choice
    tool_choice = summary_generator._create_tool_choice()
    assert tool_choice.function == {"name": "Structure"}
