"""SQLite-specific schema builder implementation."""

from core.database.interfaces.schema_builder import SchemaBuilder
from core.database.schema import ColumnDefinition, TableDefinition


class SQLiteSchemaBuilder(SchemaBuilder):
    """SQLite-specific schema builder."""

    def create_table_sql(self, table: TableDefinition) -> str:
        """Generate CREATE TABLE SQL for SQLite.

        Args:
            table: Table definition

        Returns:
            CREATE TABLE SQL statement
        """
        column_defs: list[str] = []

        for col in table.columns:
            col_def = f"{col.name} {col.type}"

            if not col.nullable:
                col_def += " NOT NULL"

            if col.primary_key:
                col_def += " PRIMARY KEY"

            if col.unique:
                col_def += " UNIQUE"

            if col.auto_increment:
                col_def += " AUTOINCREMENT"

            if col.default is not None:
                if isinstance(col.default, str):
                    col_def += f" DEFAULT '{col.default}'"
                else:
                    col_def += f" DEFAULT {col.default}"

            column_defs.append(col_def)

        columns_sql = ", ".join(column_defs)
        return f"CREATE TABLE IF NOT EXISTS {table.name} ({columns_sql})"

    def create_index_sql(
        self, table_name: str, index_name: str, columns: list[str]
    ) -> str:
        """Generate CREATE INDEX SQL for SQLite.

        Args:
            table_name: Name of the table
            index_name: Name of the index
            columns: List of column names to index

        Returns:
            CREATE INDEX SQL statement
        """
        columns_sql = ", ".join(columns)
        return (
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_sql})"
        )

    def drop_table_sql(self, table_name: str) -> str:
        """Generate DROP TABLE SQL for SQLite.

        Args:
            table_name: Name of the table to drop

        Returns:
            DROP TABLE SQL statement
        """
        return f"DROP TABLE IF EXISTS {table_name}"

    def drop_index_sql(self, index_name: str) -> str:
        """Generate DROP INDEX SQL for SQLite.

        Args:
            index_name: Name of the index to drop

        Returns:
            DROP INDEX SQL statement
        """
        return f"DROP INDEX IF EXISTS {index_name}"

    def add_column_sql(self, table_name: str, column: ColumnDefinition) -> str:
        """Generate ALTER TABLE ADD COLUMN SQL for SQLite.

        Args:
            table_name: Name of the table
            column: Column definition to add

        Returns:
            ALTER TABLE SQL statement
        """
        col_def = f"{column.name} {column.type}"

        if not column.nullable:
            col_def += " NOT NULL"

        if column.unique:
            col_def += " UNIQUE"

        if column.default is not None:
            if isinstance(column.default, str):
                col_def += f" DEFAULT '{column.default}'"
            else:
                col_def += f" DEFAULT {column.default}"

        return f"ALTER TABLE {table_name} ADD COLUMN {col_def}"
