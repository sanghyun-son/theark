"""Generic batch request builder for OpenAI API."""

from typing import Any

from core.log import get_logger
from core.models.batch import BatchRequestEntry, BatchRequestPayload
from core.models.external.openai import ChatCompletionRequest

logger = get_logger(__name__)


class BatchBuilderError(Exception):
    """Base exception for batch builder errors."""

    pass


class UnifiedBatchBuilder:
    """Generic batch request builder for OpenAI API."""

    @staticmethod
    def create_batch_from_requests(
        requests: list[dict[str, Any]],
        model: str = "gpt-4o-mini",
    ) -> BatchRequestPayload:
        """Create a batch request from a list of pre-built requests.

        Args:
            requests: List of request dictionaries with 'custom_id', 'messages', 'tools', 'tool_choice' keys
            model: Model to use for all requests

        Returns:
            Batch request payload ready for upload

        Raises:
            BatchBuilderError: If batch creation fails
        """
        if not requests:
            logger.warning("No requests provided for batch creation")
            return BatchRequestPayload(entries=[])

        logger.debug(f"Creating batch for {len(requests)} requests with model={model}")

        try:
            entries = []

            for i, request_data in enumerate(requests):
                try:
                    entry = UnifiedBatchBuilder._create_batch_entry_from_request(
                        request_data, model
                    )
                    entries.append(entry)
                    logger.debug(
                        f"Created batch entry {i+1}/{len(requests)} for "
                        f"request {request_data.get('custom_id', 'unknown')}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to create batch entry for "
                        f"request {request_data.get('custom_id', 'unknown')}: {e}"
                    )
                    # Continue with other requests instead of failing completely
                    continue

            if not entries:
                raise BatchBuilderError("No valid batch entries could be created")

            logger.info(f"Successfully created batch with {len(entries)} entries")
            return BatchRequestPayload(entries=entries)

        except Exception as e:
            logger.error(f"Batch creation failed: {e}")
            raise BatchBuilderError(f"Failed to create batch: {e}")

    @staticmethod
    def _create_batch_entry_from_request(
        request_data: dict[str, Any], model: str
    ) -> BatchRequestEntry:
        """Create a single batch entry from a request dictionary.

        Args:
            request_data: Request data with 'custom_id', 'messages', 'tools', 'tool_choice' keys
            model: Model to use

        Returns:
            Batch request entry

        Raises:
            BatchBuilderError: If entry creation fails
        """
        # Validate required fields
        required_fields = ["custom_id", "messages"]
        missing_fields = [
            field for field in required_fields if not request_data.get(field)
        ]
        if missing_fields:
            raise BatchBuilderError(f"Missing required fields: {missing_fields}")

        # Build the request payload
        payload = ChatCompletionRequest(
            model=model,
            messages=request_data["messages"],
            tools=request_data.get("tools"),
            tool_choice=request_data.get("tool_choice"),
        )

        # Convert to dict for batch entry
        body = payload.model_dump()

        # Create batch entry
        entry = BatchRequestEntry(
            custom_id=str(request_data["custom_id"]),
            method="POST",
            url="/v1/chat/completions",
            body=body,
        )

        return entry
