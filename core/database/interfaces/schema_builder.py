"""Abstract schema builder interface for different SQL backends."""

from abc import ABC, abstractmethod

from core.database.schema import ColumnDefinition, TableDefinition


class SchemaBuilder(ABC):
    """Abstract schema builder for different SQL backends."""

    @abstractmethod
    def create_table_sql(self, table: TableDefinition) -> str:
        """Generate CREATE TABLE SQL.

        Args:
            table: Table definition

        Returns:
            CREATE TABLE SQL statement
        """
        pass

    @abstractmethod
    def create_index_sql(
        self, table_name: str, index_name: str, columns: list[str]
    ) -> str:
        """Generate CREATE INDEX SQL.

        Args:
            table_name: Name of the table
            index_name: Name of the index
            columns: List of column names to index

        Returns:
            CREATE INDEX SQL statement
        """
        pass

    @abstractmethod
    def drop_table_sql(self, table_name: str) -> str:
        """Generate DROP TABLE SQL.

        Args:
            table_name: Name of the table to drop

        Returns:
            DROP TABLE SQL statement
        """
        pass

    @abstractmethod
    def drop_index_sql(self, index_name: str) -> str:
        """Generate DROP INDEX SQL.

        Args:
            index_name: Name of the index to drop

        Returns:
            DROP INDEX SQL statement
        """
        pass

    @abstractmethod
    def add_column_sql(self, table_name: str, column: ColumnDefinition) -> str:
        """Generate ALTER TABLE ADD COLUMN SQL.

        Args:
            table_name: Name of the table
            column: Column definition to add

        Returns:
            ALTER TABLE SQL statement
        """
        pass
