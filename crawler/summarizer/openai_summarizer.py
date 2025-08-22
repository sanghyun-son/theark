"""OpenAI-based abstract summarizer."""

import httpx

from .llm_tracker import LLMRequestContext
from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIFunction,
    OpenAIFunctionParameter,
    OpenAIMessage,
    OpenAITool,
    OpenAIToolChoice,
    PaperAnalysisArguments,
    PaperAnalysisProperties,
)
from .prompt import RELEVANCE_DESCRIPTION, SYSTEM_PROMPT, USER_PROMPT
from .summarizer import (
    AbstractSummarizer,
    StructuredSummary,
    SummaryRequest,
    SummaryResponse,
)


class OpenAISummarizer(AbstractSummarizer):
    """OpenAI-based implementation of abstract summarizer."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        """Initialize the OpenAI summarizer."""
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def summarize(self, request: SummaryRequest) -> SummaryResponse:
        """Summarize the given abstract using OpenAI API."""
        # Track the LLM request
        with LLMRequestContext(
            model=request.model,
            custom_id=request.custom_id,
            provider="openai",
            endpoint="/v1/chat/completions",
            is_batched=False,
            request_type="chat",
            metadata={
                "use_tools": request.use_tools,
                "language": request.language,
                "content_length": len(request.content),
            },
        ) as llm_context:
            # Create messages
            messages = [
                OpenAIMessage(
                    role="system",
                    content=SYSTEM_PROMPT.format(language=request.language),
                ),
                OpenAIMessage(
                    role="user",
                    content=USER_PROMPT.format(
                        language=request.language,
                        interest_section=request.interest_section,
                        content=request.content,
                    ),
                ),
            ]

            # Create request payload
            payload = ChatCompletionRequest(
                model=request.model,
                messages=messages,
            )

            # Add tools if requested
            if request.use_tools:
                function_parameters = OpenAIFunctionParameter(
                    type="object",
                    description="Paper analysis parameters",
                    properties=PaperAnalysisProperties.create_paper_analysis_schema(
                        RELEVANCE_DESCRIPTION
                    ),
                    required=PaperAnalysisProperties.get_required_fields(),
                )

                function = OpenAIFunction(
                    name="Structure",
                    description="Analyze paper abstract and extract key information",
                    parameters=function_parameters,
                )

                tool = OpenAITool(function=function)
                tool_choice = OpenAIToolChoice(function={"name": "Structure"})

                payload.tools = [tool]
                payload.tool_choice = tool_choice

            # Make the API request
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload.model_dump(),
            )

            # Update HTTP status in tracking
            llm_context.update_http_status(response.status_code)

            if response.status_code != 200:
                raise Exception(
                    f"OpenAI API error: {response.status_code} - {response.text}"
                )

            response_data = response.json()
            chat_response = ChatCompletionResponse(**response_data)
            choice = chat_response.choices[0]
            message = choice.message

            # Update token usage in tracking
            if chat_response.usage:
                llm_context.update_tokens(
                    {
                        "prompt_tokens": chat_response.usage.prompt_tokens,
                        "completion_tokens": chat_response.usage.completion_tokens,
                        "total_tokens": chat_response.usage.total_tokens,
                    }
                )

            # Parse the response based on whether tools were used
            if request.use_tools and message.tool_calls:
                # Structured response with function calling
                tool_call = message.tool_calls[0]

                # Use Pydantic validation for function arguments
                analysis_args = PaperAnalysisArguments.from_json_string(
                    tool_call.function.arguments
                )

                # Convert to StructuredSummary (both inherit from PaperAnalysisData)
                structured_summary = StructuredSummary(**analysis_args.model_dump())

                return SummaryResponse(
                    custom_id=request.custom_id,
                    structured_summary=structured_summary,
                    original_length=len(request.content),
                    summary_length=len(analysis_args.tldr),
                    metadata={
                        "model": request.model,
                        "usage": chat_response.usage.model_dump(),
                        "finish_reason": choice.finish_reason,
                    },
                )
            else:
                # Regular text response
                content = message.content or ""
                return SummaryResponse(
                    custom_id=request.custom_id,
                    summary=content,
                    original_length=len(request.content),
                    summary_length=len(content),
                    metadata={
                        "model": request.model,
                        "usage": chat_response.usage.model_dump(),
                        "finish_reason": choice.finish_reason,
                    },
                )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
