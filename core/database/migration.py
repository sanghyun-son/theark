"""Database migration utilities."""

from typing import Any, Callable

from core.database.interfaces.connection import DatabaseConnection


class MigrationManager:
    """Manage database migrations."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        self.migrations_table = "schema_migrations"

    async def ensure_migrations_table(self) -> None:
        """Create migrations table if it doesn't exist."""
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.migrations_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        await self.db_connection.execute(create_sql, None)

    async def get_applied_migrations(self) -> list[str]:
        """Get list of applied migration versions."""
        query = f"SELECT version FROM {self.migrations_table} ORDER BY id"
        rows = await self.db_connection.fetch_all(query, None)
        return [row["version"] for row in rows]

    async def apply_migration(
        self, version: str, migration_func: Callable[[DatabaseConnection], Any]
    ) -> None:
        """Apply a single migration.

        Args:
            version: Migration version identifier
            migration_func: Async function that performs the migration
        """
        await migration_func(self.db_connection)

        insert_sql = f"INSERT INTO {self.migrations_table} (version) VALUES (?)"
        await self.db_connection.execute(insert_sql, (version,))

    async def run_migrations(
        self, migrations: dict[str, Callable[[DatabaseConnection], Any]]
    ) -> None:
        """Run all pending migrations.

        Args:
            migrations: Dictionary mapping version to migration function
        """
        await self.ensure_migrations_table()
        applied = await self.get_applied_migrations()

        for version, migration_func in sorted(migrations.items()):
            if version not in applied:
                await self.apply_migration(version, migration_func)

    async def get_migration_status(
        self, migrations: dict[str, Callable[[DatabaseConnection], Any]]
    ) -> dict[str, bool]:
        """Get status of all known migrations.

        Args:
            migrations: Dictionary of known migrations

        Returns:
            Dictionary mapping version to applied status
        """
        await self.ensure_migrations_table()
        applied = await self.get_applied_migrations()

        # Get all known migrations from the migrations dict
        all_migrations = set(migrations.keys())

        return {version: version in applied for version in all_migrations}
