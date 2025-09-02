"""Utility functions for parsing OpenAI responses with Pydantic validation."""

from typing import Any, Union

from core.log import get_logger
from core.models.external.openai import PaperAnalysis

logger = get_logger(__name__)

# Type for models that have from_json_string method
JsonParseableModel = Union[type[PaperAnalysis]]  # Add more models here as needed


def parse_tool_call_response(
    tool_call: Any,
    response_model: JsonParseableModel,
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
        logger.warning(f"Failed to parse tool response{e}")
        return None
