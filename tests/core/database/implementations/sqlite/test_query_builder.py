"""Tests for SQLite query builder."""

import pytest

from core.database.implementations.sqlite.query_builder import SQLiteQueryBuilder


@pytest.fixture
def query_builder() -> SQLiteQueryBuilder:
    """Create SQLite query builder instance."""
    return SQLiteQueryBuilder()


def test_select_basic(query_builder: SQLiteQueryBuilder) -> None:
    """Test basic SELECT query."""
    query, params = query_builder.select("users")

    assert query == "SELECT * FROM users"
    assert params == {}


def test_select_with_columns(query_builder: SQLiteQueryBuilder) -> None:
    """Test SELECT query with specific columns."""
    query, params = query_builder.select("users", columns=["id", "name"])

    assert query == "SELECT id, name FROM users"
    assert params == {}


def test_select_with_where(query_builder: SQLiteQueryBuilder) -> None:
    """Test SELECT query with WHERE clause."""
    query, params = query_builder.select("users", where={"name": "John"})

    assert "SELECT * FROM users WHERE name = :param_name" in query
    assert params == {"param_name": "John"}


def test_select_with_order_by(query_builder: SQLiteQueryBuilder) -> None:
    """Test SELECT query with ORDER BY clause."""
    query, params = query_builder.select("users", order_by=["name", "age DESC"])

    assert query == "SELECT * FROM users ORDER BY name, age DESC"
    assert params == {}


def test_select_with_limit(query_builder: SQLiteQueryBuilder) -> None:
    """Test SELECT query with LIMIT clause."""
    query, params = query_builder.select("users", limit=10)

    assert query == "SELECT * FROM users LIMIT 10"
    assert params == {}


def test_select_with_limit_and_offset(query_builder: SQLiteQueryBuilder) -> None:
    """Test SELECT query with LIMIT and OFFSET clauses."""
    query, params = query_builder.select("users", limit=10, offset=20)

    assert query == "SELECT * FROM users LIMIT 10 OFFSET 20"
    assert params == {}


def test_select_complex(query_builder: SQLiteQueryBuilder) -> None:
    """Test complex SELECT query with all clauses."""
    query, params = query_builder.select(
        "users",
        columns=["id", "name"],
        where={"age": 30, "active": True},
        order_by=["name"],
        limit=5,
        offset=10,
    )

    assert "SELECT id, name FROM users" in query
    assert "WHERE age = :param_age AND active = :param_active" in query
    assert "ORDER BY name" in query
    assert "LIMIT 5 OFFSET 10" in query
    assert params == {"param_age": 30, "param_active": True}


def test_insert_basic(query_builder: SQLiteQueryBuilder) -> None:
    """Test basic INSERT query."""
    data = {"name": "John", "email": "john@example.com"}
    query, params = query_builder.insert("users", data)

    assert "INSERT INTO users (name, email) VALUES (:name, :email)" in query
    assert params == data


def test_insert_empty_data(query_builder: SQLiteQueryBuilder) -> None:
    """Test INSERT query with empty data."""
    with pytest.raises(ValueError, match="Cannot insert empty data"):
        query_builder.insert("users", {})


def test_update_basic(query_builder: SQLiteQueryBuilder) -> None:
    """Test basic UPDATE query."""
    data = {"name": "Jane", "email": "jane@example.com"}
    query, params = query_builder.update("users", data)

    assert "UPDATE users SET name = :name, email = :email" in query
    assert params == data


def test_update_with_where(query_builder: SQLiteQueryBuilder) -> None:
    """Test UPDATE query with WHERE clause."""
    data = {"name": "Jane"}
    where = {"id": 1}
    query, params = query_builder.update("users", data, where)

    assert "UPDATE users SET name = :name" in query
    assert "WHERE id = :param_id" in query
    assert params == {"name": "Jane", "param_id": 1}


def test_update_empty_data(query_builder: SQLiteQueryBuilder) -> None:
    """Test UPDATE query with empty data."""
    with pytest.raises(ValueError, match="Cannot update with empty data"):
        query_builder.update("users", {})


def test_delete_basic(query_builder: SQLiteQueryBuilder) -> None:
    """Test basic DELETE query."""
    query, params = query_builder.delete("users")

    assert query == "DELETE FROM users"
    assert params == {}


def test_delete_with_where(query_builder: SQLiteQueryBuilder) -> None:
    """Test DELETE query with WHERE clause."""
    where = {"id": 1}
    query, params = query_builder.delete("users", where)

    assert "DELETE FROM users WHERE id = :param_id" in query
    assert params == {"param_id": 1}


def test_count_basic(query_builder: SQLiteQueryBuilder) -> None:
    """Test basic COUNT query."""
    query, params = query_builder.count("users")

    assert query == "SELECT COUNT(*) FROM users"
    assert params == {}


def test_count_with_where(query_builder: SQLiteQueryBuilder) -> None:
    """Test COUNT query with WHERE clause."""
    where = {"active": True}
    query, params = query_builder.count("users", where)

    assert "SELECT COUNT(*) FROM users WHERE active = :param_active" in query
    assert params == {"param_active": True}
