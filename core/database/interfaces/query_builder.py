"""Abstract query builder interface for different SQL backends."""

from abc import ABC, abstractmethod
from typing import Any

from core.types import DatabaseParamType


class QueryBuilder(ABC):
    """Abstract query builder for different SQL backends."""

    @abstractmethod
    def select(
        self,
        table: str,
        columns: list[str] | None = None,
        where: dict[str, Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[str, DatabaseParamType]:
        """Build SELECT query.

        Args:
            table: Table name
            columns: List of columns to select (None for all)
            where: WHERE conditions dictionary
            order_by: ORDER BY fields list
            limit: LIMIT value
            offset: OFFSET value

        Returns:
            Tuple of (query, parameters)
        """
        pass

    @abstractmethod
    def insert(self, table: str, data: dict[str, Any]) -> tuple[str, DatabaseParamType]:
        """Build INSERT query.

        Args:
            table: Table name
            data: Data dictionary to insert

        Returns:
            Tuple of (query, parameters)
        """
        pass

    @abstractmethod
    def update(
        self,
        table: str,
        data: dict[str, Any],
        where: dict[str, Any] | None = None,
    ) -> tuple[str, DatabaseParamType]:
        """Build UPDATE query.

        Args:
            table: Table name
            data: Data dictionary to update
            where: WHERE conditions dictionary

        Returns:
            Tuple of (query, parameters)
        """
        pass

    @abstractmethod
    def delete(
        self, table: str, where: dict[str, Any] | None = None
    ) -> tuple[str, DatabaseParamType]:
        """Build DELETE query.

        Args:
            table: Table name
            where: WHERE conditions dictionary

        Returns:
            Tuple of (query, parameters)
        """
        pass

    @abstractmethod
    def count(
        self, table: str, where: dict[str, Any] | None = None
    ) -> tuple[str, DatabaseParamType]:
        """Build COUNT query.

        Args:
            table: Table name
            where: WHERE conditions dictionary

        Returns:
            Tuple of (query, parameters)
        """
        pass
