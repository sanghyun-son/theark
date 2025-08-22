"""Pydantic models for OpenAI API payloads and responses."""

from typing import Literal

from pydantic import BaseModel, Field


class OpenAIMessage(BaseModel):
    """OpenAI API message model."""

    role: Literal["system", "user", "assistant"]
    content: str | None = None
    tool_calls: list["OpenAIToolCall"] | None = None


class OpenAIPropertyDefinition(BaseModel):
    """OpenAI API property definition model."""

    type: str
    description: str


class PaperAnalysisData(BaseModel):
    """Shared base model for paper analysis data."""

    tldr: str = Field(description="generate a too long; didn't read summary")
    motivation: str = Field(description="describe the motivation in this paper")
    method: str = Field(description="method of this paper")
    result: str = Field(description="result of this paper")
    conclusion: str = Field(description="conclusion of this paper")
    relevance: str = Field(
        description="relevance level between the abstract and user interests"
    )


class PaperAnalysisProperties(BaseModel):
    """Reusable paper analysis properties for OpenAI function calling."""

    @classmethod
    def create_paper_analysis_schema(
        cls, relevance_description: str
    ) -> dict[str, OpenAIPropertyDefinition]:
        """Create the standard paper analysis properties schema."""
        return {
            "tldr": OpenAIPropertyDefinition(
                type="string",
                description="generate a too long; didn't read summary",
            ),
            "motivation": OpenAIPropertyDefinition(
                type="string",
                description="describe the motivation in this paper",
            ),
            "method": OpenAIPropertyDefinition(
                type="string",
                description="method of this paper",
            ),
            "result": OpenAIPropertyDefinition(
                type="string",
                description="result of this paper",
            ),
            "conclusion": OpenAIPropertyDefinition(
                type="string",
                description="conclusion of this paper",
            ),
            "relevance": OpenAIPropertyDefinition(
                type="string",
                description=relevance_description,
            ),
        }

    @classmethod
    def get_required_fields(cls) -> list[str]:
        """Get the list of required fields for paper analysis."""
        return [
            "tldr",
            "motivation",
            "method",
            "result",
            "conclusion",
            "relevance",
        ]


class OpenAIFunctionParameter(BaseModel):
    """OpenAI API function parameter model."""

    type: str
    description: str
    properties: dict[str, OpenAIPropertyDefinition]
    required: list[str]


class OpenAIFunction(BaseModel):
    """OpenAI API function model."""

    name: str
    description: str
    parameters: OpenAIFunctionParameter


class OpenAITool(BaseModel):
    """OpenAI API tool model."""

    type: Literal["function"] = "function"
    function: OpenAIFunction


class OpenAIToolChoice(BaseModel):
    """OpenAI API tool choice model."""

    type: Literal["function"] = "function"
    function: dict[str, str]


class OpenAIFunctionCall(BaseModel):
    """OpenAI API function call model within tool calls."""

    name: str
    arguments: str


class OpenAIToolCall(BaseModel):
    """OpenAI API tool call model."""

    id: str
    type: Literal["function"] = "function"
    function: OpenAIFunctionCall


class PaperAnalysisArguments(PaperAnalysisData):
    """Validated paper analysis arguments from OpenAI function calls."""

    @classmethod
    def from_json_string(cls, json_str: str) -> "PaperAnalysisArguments":
        """Create PaperAnalysisArguments from a JSON string with validation."""
        import json

        data = json.loads(json_str)
        return cls(**data)


class ChatCompletionRequest(BaseModel):
    """OpenAI API chat completion request model."""

    model: str
    messages: list[OpenAIMessage]
    tools: list[OpenAITool] | None = None
    tool_choice: OpenAIToolChoice | None = None


class OpenAIChoice(BaseModel):
    """OpenAI API choice model."""

    index: int
    message: OpenAIMessage
    finish_reason: str


class OpenAITokenUsage(BaseModel):
    """OpenAI API token usage model."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI API chat completion response model."""

    id: str
    object: str
    created: int
    model: str
    choices: list[OpenAIChoice]
    usage: OpenAITokenUsage
