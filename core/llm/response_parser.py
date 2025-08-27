"""Utility functions for parsing OpenAI responses with Pydantic validation."""

from typing import Any, Union

from core.log import get_logger
from core.models.external.openai import ChatCompletionResponse, PaperAnalysis
from core.models.summarization import SummaryResponse

logger = get_logger(__name__)

# Type for models that have from_json_string method
JsonParseableModel = Union[type[PaperAnalysis]]  # Add more models here as needed


def parse_tool_call_response(
    tool_call: Any,
    response_model: JsonParseableModel,
    custom_id: str | None = None,
) -> PaperAnalysis | None:
    """Parse tool call response using Pydantic validation.

    Args:
        tool_call: OpenAI tool call object
        response_model: Pydantic model class to validate against
        custom_id: Custom identifier for logging

    Returns:
        Validated response model instance or None if parsing fails
    """
    try:
        # Use the model's custom parsing method
        return response_model.from_json_string(tool_call.function.arguments)
    except Exception as e:
        logger.warning(
            f"Failed to parse tool response for {custom_id or 'unknown'}: {e}"
        )
        return None


def parse_summary_response(
    response: ChatCompletionResponse,
    original_content: str,
    custom_id: str | None = None,
    model: str = "gpt-4o-mini",
    use_tools: bool = True,
) -> SummaryResponse:
    """Parse OpenAI chat completion response into SummaryResponse."""
    if not response.choices or not response.choices[0].message:
        raise ValueError("No response content received")

    message = response.choices[0].message
    summary_content = message.content or ""

    # Handle tool responses with Pydantic validation
    structured_summary = None
    if message.tool_calls and use_tools:
        tool_call = message.tool_calls[0]
        if tool_call.function.name == "Structure":
            structured_summary = parse_tool_call_response(
                tool_call, PaperAnalysis, custom_id
            )
            if structured_summary:
                summary_content = structured_summary.tldr

    return SummaryResponse(
        custom_id=custom_id or "",
        summary=summary_content,
        structured_summary=structured_summary,
        original_length=len(original_content),
        summary_length=len(summary_content),
        metadata={"model": model, "use_tools": use_tools},
    )
