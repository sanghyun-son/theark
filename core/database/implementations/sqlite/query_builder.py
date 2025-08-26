"""SQLite-specific query builder implementation."""

from typing import Any

from core.database.interfaces.query_builder import QueryBuilder
from core.database.utils import (
    build_limit_clause,
    build_order_by_clause,
    build_where_clause,
)
from core.types import DatabaseParamType


class SQLiteQueryBuilder(QueryBuilder):
    """SQLite-specific query builder."""

    def select(
        self,
        table: str,
        columns: list[str] | None = None,
        where: dict[str, Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[str, DatabaseParamType]:
        """Build SELECT query for SQLite.

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
        cols = "*" if columns is None else ", ".join(columns)
        query = f"SELECT {cols} FROM {table}"
        params: DatabaseParamType = {}

        if where:
            where_clause, where_params = build_where_clause(where)
            query += f" {where_clause}"
            params = where_params

        if order_by:
            order_clause = build_order_by_clause(order_by)
            query += f" {order_clause}"

        if limit is not None:
            limit_clause = build_limit_clause(limit, offset)
            query += f" {limit_clause}"

        return query, params

    def insert(self, table: str, data: dict[str, Any]) -> tuple[str, DatabaseParamType]:
        """Build INSERT query for SQLite.

        Args:
            table: Table name
            data: Data dictionary to insert

        Returns:
            Tuple of (query, parameters)
        """
        if not data:
            raise ValueError("Cannot insert empty data")

        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]

        query = (
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)})"
        )

        return query, data

    def update(
        self,
        table: str,
        data: dict[str, Any],
        where: dict[str, Any] | None = None,
    ) -> tuple[str, DatabaseParamType]:
        """Build UPDATE query for SQLite.

        Args:
            table: Table name
            data: Data dictionary to update
            where: WHERE conditions dictionary

        Returns:
            Tuple of (query, parameters)
        """
        if not data:
            raise ValueError("Cannot update with empty data")

        set_clause = ", ".join([f"{col} = :{col}" for col in data.keys()])
        query = f"UPDATE {table} SET {set_clause}"
        params = data.copy()

        if where:
            where_clause, where_params = build_where_clause(where)
            query += f" {where_clause}"
            params.update(where_params)

        return query, params

    def delete(
        self, table: str, where: dict[str, Any] | None = None
    ) -> tuple[str, DatabaseParamType]:
        """Build DELETE query for SQLite.

        Args:
            table: Table name
            where: WHERE conditions dictionary

        Returns:
            Tuple of (query, parameters)
        """
        query = f"DELETE FROM {table}"
        params: DatabaseParamType = {}

        if where:
            where_clause, where_params = build_where_clause(where)
            query += f" {where_clause}"
            params = where_params

        return query, params

    def count(
        self, table: str, where: dict[str, Any] | None = None
    ) -> tuple[str, DatabaseParamType]:
        """Build COUNT query for SQLite.

        Args:
            table: Table name
            where: WHERE conditions dictionary

        Returns:
            Tuple of (query, parameters)
        """
        query = f"SELECT COUNT(*) FROM {table}"
        params: DatabaseParamType = {}

        if where:
            where_clause, where_params = build_where_clause(where)
            query += f" {where_clause}"
            params = where_params

        return query, params
