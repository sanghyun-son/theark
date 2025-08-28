"""OpenAI API models for external service integration."""

from typing import Any, Literal

from pydantic import BaseModel, Field

# OpenAI API literal types
CompletionWindow = Literal["24h"]
BatchEndpoint = Literal[
    "/v1/responses", "/v1/chat/completions", "/v1/embeddings", "/v1/completions"
]
FilePurpose = Literal[
    "assistants", "batch", "fine-tune", "vision", "user_data", "evals"
]


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
    def create_paper_analysis_schema(
        cls, language: str
    ) -> dict[str, OpenAIPropertyDefinition]:
        """Create the standard paper analysis properties schema."""
        return {
            "tldr": OpenAIPropertyDefinition(
                type="string",
                description=f"Generate a too long; didn't read summary in {language}.",
            ),
            "motivation": OpenAIPropertyDefinition(
                type="string",
                description=f"Describe the motivation in this paper in {language}.",
            ),
            "method": OpenAIPropertyDefinition(
                type="string",
                description=(
                    f"Describe the method of this paper in detail in {language}."
                ),
            ),
            "result": OpenAIPropertyDefinition(
                type="string",
                description=(
                    f"Describe the result "
                    f"and achievement of this paper in {language}."
                ),
            ),
            "conclusion": OpenAIPropertyDefinition(
                type="string",
                description=(
                    f"Describe the conclusion "
                    f"and implication of this paper in {language}."
                ),
            ),
            "relevance": OpenAIPropertyDefinition(
                type="integer",
                description=(
                    "Relevance level (1-10) between the abstract and user interests."
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


class BatchRequest(BaseModel):
    """OpenAI Batch API request model."""

    id: str | None = Field(default=None, description="Unique batch request ID")
    input_file_id: str = Field(..., description="ID of the uploaded input file")
    endpoint: str = Field(
        default="/v1/chat/completions", description="API endpoint for batch processing"
    )
    completion_window: str = Field(
        default="24h", description="Time window for batch completion (24h, 24h, 24h)"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata for the batch request"
    )


class BatchResponse(BaseModel):
    """OpenAI Batch API response model."""

    id: str = Field(..., description="Unique batch request ID")
    object: str = Field(default="batch", description="Object type")
    endpoint: str = Field(..., description="API endpoint used")
    errors: dict[str, Any] | None = Field(
        default=None, description="Error information if batch creation failed"
    )
    input_file_id: str = Field(..., description="ID of the input file")
    completion_window: str = Field(..., description="Completion window")
    status: str = Field(
        ...,
        description="Batch status: validating, failed, in_progress, completed, expired",
    )
    output_file_id: str | None = Field(
        default=None, description="ID of the output file with results"
    )
    error_file_id: str | None = Field(
        default=None, description="ID of the error file if any"
    )
    created_at: int = Field(..., description="Unix timestamp when batch was created")
    in_progress_at: int | None = Field(
        default=None, description="Unix timestamp when batch started processing"
    )
    expires_at: int | None = Field(
        default=None, description="Unix timestamp when batch expires"
    )
    finalizing_at: int | None = Field(
        default=None, description="Unix timestamp when batch started finalizing"
    )
    completed_at: int | None = Field(
        default=None, description="Unix timestamp when batch completed"
    )
    request_counts: dict[str, int] | None = Field(
        default=None, description="Counts of requests by status"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )
