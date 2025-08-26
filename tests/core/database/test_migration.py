"""Tests for database migration utilities."""

import pytest
from unittest.mock import AsyncMock

from core.database.migration import MigrationManager
from core.database.interfaces.connection import DatabaseConnection


@pytest.fixture
def mock_connection() -> AsyncMock:
    """Create mock database connection."""
    connection = AsyncMock(spec=DatabaseConnection)
    connection.fetch_all.return_value = [
        {"version": "001_initial"},
        {"version": "002_add_users"},
    ]
    return connection


@pytest.fixture
def migration_manager(mock_connection: AsyncMock) -> MigrationManager:
    """Create MigrationManager instance."""
    return MigrationManager(mock_connection)


@pytest.mark.asyncio
async def test_ensure_migrations_table(
    migration_manager: MigrationManager, mock_connection: AsyncMock
) -> None:
    """Test creating migrations table."""
    await migration_manager.ensure_migrations_table()

    mock_connection.execute.assert_called_once()
    call_args = mock_connection.execute.call_args
    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in call_args[0][0]


@pytest.mark.asyncio
async def test_get_applied_migrations(
    migration_manager: MigrationManager, mock_connection: AsyncMock
) -> None:
    """Test getting applied migrations."""
    result = await migration_manager.get_applied_migrations()

    assert result == ["001_initial", "002_add_users"]
    mock_connection.fetch_all.assert_called_once_with(
        "SELECT version FROM schema_migrations ORDER BY id", None
    )


@pytest.mark.asyncio
async def test_apply_migration(
    migration_manager: MigrationManager, mock_connection: AsyncMock
) -> None:
    """Test applying a single migration."""
    migration_func = AsyncMock()

    await migration_manager.apply_migration("003_add_papers", migration_func)

    # Check that migration function was called
    migration_func.assert_called_once_with(mock_connection)

    # Check that migration was recorded
    mock_connection.execute.assert_called_with(
        "INSERT INTO schema_migrations (version) VALUES (?)", ("003_add_papers",)
    )


@pytest.mark.asyncio
async def test_run_migrations_with_pending_migrations(
    migration_manager: MigrationManager, mock_connection: AsyncMock
) -> None:
    """Test running migrations with pending migrations."""
    # Mock get_applied_migrations to return only one applied migration
    mock_connection.fetch_all.return_value = [{"version": "001_initial"}]

    migrations = {
        "001_initial": AsyncMock(),
        "002_add_users": AsyncMock(),
        "003_add_papers": AsyncMock(),
    }

    await migration_manager.run_migrations(migrations)

    # Check that only pending migrations were applied
    migrations["001_initial"].assert_not_called()  # Already applied
    migrations["002_add_users"].assert_called_once_with(mock_connection)
    migrations["003_add_papers"].assert_called_once_with(mock_connection)


@pytest.mark.asyncio
async def test_run_migrations_with_no_pending_migrations(
    migration_manager: MigrationManager, mock_connection: AsyncMock
) -> None:
    """Test running migrations when all are already applied."""
    # Mock get_applied_migrations to return all migrations
    mock_connection.fetch_all.return_value = [
        {"version": "001_initial"},
        {"version": "002_add_users"},
    ]

    migrations = {
        "001_initial": AsyncMock(),
        "002_add_users": AsyncMock(),
    }

    await migration_manager.run_migrations(migrations)

    # Check that no migrations were applied
    migrations["001_initial"].assert_not_called()
    migrations["002_add_users"].assert_not_called()


@pytest.mark.asyncio
async def test_get_migration_status(
    migration_manager: MigrationManager, mock_connection: AsyncMock
) -> None:
    """Test getting migration status."""
    # Mock get_applied_migrations to return some applied migrations
    mock_connection.fetch_all.return_value = [
        {"version": "001_initial"},
        {"version": "002_add_users"},
    ]

    migrations = {
        "001_initial": AsyncMock(),
        "002_add_users": AsyncMock(),
        "003_add_papers": AsyncMock(),
    }

    result = await migration_manager.get_migration_status(migrations)

    expected = {
        "001_initial": True,
        "002_add_users": True,
        "003_add_papers": False,
    }
    assert result == expected


@pytest.mark.asyncio
async def test_migrations_run_in_order(
    migration_manager: MigrationManager, mock_connection: AsyncMock
) -> None:
    """Test that migrations run in alphabetical order."""
    # Mock get_applied_migrations to return empty list
    mock_connection.fetch_all.return_value = []

    call_order = []

    async def migration_001(conn: DatabaseConnection) -> None:
        call_order.append("001_initial")

    async def migration_002(conn: DatabaseConnection) -> None:
        call_order.append("002_add_users")

    async def migration_003(conn: DatabaseConnection) -> None:
        call_order.append("003_add_papers")

    migrations = {
        "003_add_papers": migration_003,
        "001_initial": migration_001,
        "002_add_users": migration_002,
    }

    await migration_manager.run_migrations(migrations)

    # Check that migrations ran in alphabetical order
    assert call_order == ["001_initial", "002_add_users", "003_add_papers"]
