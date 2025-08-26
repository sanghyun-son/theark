"""Tests for SQLite schema builder."""

import pytest

from core.database.implementations.sqlite.schema_builder import SQLiteSchemaBuilder
from core.database.schema import ColumnDefinition, TableDefinition


@pytest.fixture
def schema_builder() -> SQLiteSchemaBuilder:
    """Create SQLite schema builder instance."""
    return SQLiteSchemaBuilder()


@pytest.fixture
def sample_columns() -> list[ColumnDefinition]:
    """Sample column definitions."""
    return [
        ColumnDefinition("id", "INTEGER", primary_key=True, auto_increment=True),
        ColumnDefinition("name", "TEXT", nullable=False),
        ColumnDefinition("email", "TEXT", unique=True),
        ColumnDefinition("age", "INTEGER", default=0),
        ColumnDefinition("created_at", "TIMESTAMP", default="CURRENT_TIMESTAMP"),
    ]


@pytest.fixture
def sample_table(sample_columns: list[ColumnDefinition]) -> TableDefinition:
    """Sample table definition."""
    return TableDefinition(
        name="users",
        columns=sample_columns,
        indexes=["idx_users_email", "idx_users_name"],
    )


def test_create_table_sql_basic(
    schema_builder: SQLiteSchemaBuilder, sample_table: TableDefinition
) -> None:
    """Test creating basic CREATE TABLE SQL."""
    sql = schema_builder.create_table_sql(sample_table)

    assert "CREATE TABLE IF NOT EXISTS users" in sql
    assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in sql
    assert "name TEXT NOT NULL" in sql
    assert "email TEXT UNIQUE" in sql
    assert "age INTEGER DEFAULT 0" in sql
    assert "created_at TIMESTAMP DEFAULT 'CURRENT_TIMESTAMP'" in sql


def test_create_table_sql_with_string_default(
    schema_builder: SQLiteSchemaBuilder,
) -> None:
    """Test creating table with string default value."""
    columns = [
        ColumnDefinition("name", "TEXT", default="John Doe"),
    ]
    table = TableDefinition("users", columns)

    sql = schema_builder.create_table_sql(table)

    assert "name TEXT DEFAULT 'John Doe'" in sql


def test_create_table_sql_with_numeric_default(
    schema_builder: SQLiteSchemaBuilder,
) -> None:
    """Test creating table with numeric default value."""
    columns = [
        ColumnDefinition("age", "INTEGER", default=25),
    ]
    table = TableDefinition("users", columns)

    sql = schema_builder.create_table_sql(table)

    assert "age INTEGER DEFAULT 25" in sql


def test_create_table_sql_with_nullable_column(
    schema_builder: SQLiteSchemaBuilder,
) -> None:
    """Test creating table with nullable column."""
    columns = [
        ColumnDefinition("description", "TEXT", nullable=True),
    ]
    table = TableDefinition("posts", columns)

    sql = schema_builder.create_table_sql(table)

    assert "description TEXT" in sql  # No NOT NULL constraint


def test_create_table_sql_with_non_nullable_column(
    schema_builder: SQLiteSchemaBuilder,
) -> None:
    """Test creating table with non-nullable column."""
    columns = [
        ColumnDefinition("title", "TEXT", nullable=False),
    ]
    table = TableDefinition("posts", columns)

    sql = schema_builder.create_table_sql(table)

    assert "title TEXT NOT NULL" in sql


def test_create_index_sql(schema_builder: SQLiteSchemaBuilder) -> None:
    """Test creating CREATE INDEX SQL."""
    sql = schema_builder.create_index_sql("users", "idx_users_email", ["email"])

    assert sql == "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)"


def test_create_index_sql_multiple_columns(schema_builder: SQLiteSchemaBuilder) -> None:
    """Test creating CREATE INDEX SQL with multiple columns."""
    sql = schema_builder.create_index_sql(
        "users", "idx_users_name_email", ["name", "email"]
    )

    assert (
        sql == "CREATE INDEX IF NOT EXISTS idx_users_name_email ON users (name, email)"
    )


def test_drop_table_sql(schema_builder: SQLiteSchemaBuilder) -> None:
    """Test creating DROP TABLE SQL."""
    sql = schema_builder.drop_table_sql("users")

    assert sql == "DROP TABLE IF EXISTS users"


def test_drop_index_sql(schema_builder: SQLiteSchemaBuilder) -> None:
    """Test creating DROP INDEX SQL."""
    sql = schema_builder.drop_index_sql("idx_users_email")

    assert sql == "DROP INDEX IF EXISTS idx_users_email"


def test_add_column_sql_basic(schema_builder: SQLiteSchemaBuilder) -> None:
    """Test creating ALTER TABLE ADD COLUMN SQL."""
    column = ColumnDefinition("phone", "TEXT")
    sql = schema_builder.add_column_sql("users", column)

    assert sql == "ALTER TABLE users ADD COLUMN phone TEXT"


def test_add_column_sql_with_not_null(schema_builder: SQLiteSchemaBuilder) -> None:
    """Test creating ALTER TABLE ADD COLUMN SQL with NOT NULL."""
    column = ColumnDefinition("phone", "TEXT", nullable=False)
    sql = schema_builder.add_column_sql("users", column)

    assert sql == "ALTER TABLE users ADD COLUMN phone TEXT NOT NULL"


def test_add_column_sql_with_unique(schema_builder: SQLiteSchemaBuilder) -> None:
    """Test creating ALTER TABLE ADD COLUMN SQL with UNIQUE."""
    column = ColumnDefinition("phone", "TEXT", unique=True)
    sql = schema_builder.add_column_sql("users", column)

    assert sql == "ALTER TABLE users ADD COLUMN phone TEXT UNIQUE"


def test_add_column_sql_with_string_default(
    schema_builder: SQLiteSchemaBuilder,
) -> None:
    """Test creating ALTER TABLE ADD COLUMN SQL with string default."""
    column = ColumnDefinition("status", "TEXT", default="active")
    sql = schema_builder.add_column_sql("users", column)

    assert sql == "ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'"


def test_add_column_sql_with_numeric_default(
    schema_builder: SQLiteSchemaBuilder,
) -> None:
    """Test creating ALTER TABLE ADD COLUMN SQL with numeric default."""
    column = ColumnDefinition("score", "INTEGER", default=100)
    sql = schema_builder.add_column_sql("users", column)

    assert sql == "ALTER TABLE users ADD COLUMN score INTEGER DEFAULT 100"


def test_add_column_sql_with_not_null_and_unique(
    schema_builder: SQLiteSchemaBuilder,
) -> None:
    """Test creating ALTER TABLE ADD COLUMN SQL with NOT NULL and UNIQUE."""
    column = ColumnDefinition("username", "TEXT", nullable=False, unique=True)
    sql = schema_builder.add_column_sql("users", column)

    assert sql == "ALTER TABLE users ADD COLUMN username TEXT NOT NULL UNIQUE"
