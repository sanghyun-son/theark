"""OpenAI API models for external service integration."""

from typing import Literal

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Generic token usage model for LLM requests."""

    prompt_tokens: int = Field(description="Number of tokens in the prompt")
    completion_tokens: int = Field(description="Number of tokens in the completion")
    total_tokens: int = Field(description="Total number of tokens used")


class OpenAIMessage(BaseModel):
    """OpenAI API message model."""

    role: Literal["system", "user", "assistant"]
    content: str | None = None
    tool_calls: list["OpenAIToolCall"] | None = None


class OpenAIPropertyDefinition(BaseModel):
    """OpenAI API property definition model."""

    type: str
    description: str


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


class OpenAITokenUsage(TokenUsage):
    """OpenAI API token usage model (extends generic TokenUsage)."""

    # Inherits all fields from TokenUsage
    pass


class OpenAIChoice(BaseModel):
    """OpenAI API choice model."""

    index: int
    message: OpenAIMessage
    finish_reason: str


class ChatCompletionRequest(BaseModel):
    """OpenAI API chat completion request model."""

    model: str
    messages: list[OpenAIMessage]
    tools: list[OpenAITool] | None = None
    tool_choice: OpenAIToolChoice | None = None


class ChatCompletionResponse(BaseModel):
    """OpenAI API chat completion response model."""

    id: str
    object: str
    created: int
    model: str
    choices: list[OpenAIChoice]
    usage: OpenAITokenUsage


class PaperAnalysis(BaseModel):
    """Paper analysis data from OpenAI function calls."""

    tldr: str = Field(description="Too long; didn't read summary")
    motivation: str = Field(description="Research motivation")
    method: str = Field(description="Methodology used")
    result: str = Field(description="Results obtained")
    conclusion: str = Field(description="Conclusions drawn")
    relevance: int = Field(description="Relevance (1-10) to user interests")

    @classmethod
    def from_json_string(cls, json_str: str) -> "PaperAnalysis":
        """Create PaperAnalysis from JSON string with validation."""
        import json

        data = json.loads(json_str)
        return cls(**data)

    @classmethod
    def create_paper_analysis_schema(cls) -> dict[str, OpenAIPropertyDefinition]:
        """Create the standard paper analysis properties schema."""
        return {
            "tldr": OpenAIPropertyDefinition(
                type="string",
                description="Generate a too long; didn't read summary in one line.",
            ),
            "motivation": OpenAIPropertyDefinition(
                type="string",
                description="Describe the motivation in this paper.",
            ),
            "method": OpenAIPropertyDefinition(
                type="string",
                description="Describe the method of this paper in detail.",
            ),
            "result": OpenAIPropertyDefinition(
                type="string",
                description="Describe the result and achievement of this paper.",
            ),
            "conclusion": OpenAIPropertyDefinition(
                type="string",
                description="Describe the conclusion and implication of this paper.",
            ),
            "relevance": OpenAIPropertyDefinition(
                type="integer",
                description=(
                    "Relevance level (1-10) " "between the abstract and user interests."
                ),
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
