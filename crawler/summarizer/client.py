"""Abstract summary client interface."""

from abc import ABC, abstractmethod

from crawler.database.llm_sqlite_manager import LLMSQLiteManager

from .summarizer import SummaryRequest, SummaryResponse


class SummaryClient(ABC):
    """Abstract interface for summary clients."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Get the model name used by this client."""
        pass

    @property
    @abstractmethod
    def use_tools(self) -> bool:
        """Get whether this client uses tools/function calling."""
        pass

    @abstractmethod
    async def summarize(
        self, request: SummaryRequest, db_manager: LLMSQLiteManager
    ) -> SummaryResponse:
        """Summarize content using the client."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client and cleanup resources."""
        pass
