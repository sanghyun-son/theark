"""Unit tests for database configuration."""

from pathlib import Path

import pytest

from crawler.database.config import (
    DatabaseConfig,
    Environment,
    get_database_dir,
    get_database_path,
    setup_database_environment,
)


class TestDatabaseConfig:
    """Test DatabaseConfig class."""

    def test_development_environment(self, tmp_path: Path) -> None:
        """Test development environment configuration."""
        # Change to tmp_path to simulate project root
        original_cwd = Path.cwd()
        try:
            Path.cwd = lambda: tmp_path

            config = DatabaseConfig("development")

            # Should create ./db directory
            expected_db_dir = tmp_path / "db"
            assert config.database_dir == expected_db_dir

            # Should use arxiv.db file
            expected_db_path = expected_db_dir / "arxiv.db"
            assert config.database_path == expected_db_path

            # Should create directory when accessed
            config.database_path
            assert expected_db_dir.exists()

        finally:
            # Restore original cwd function
            Path.cwd = lambda: original_cwd

    def test_production_environment(self, tmp_path: Path) -> None:
        """Test production environment configuration."""
        # Change to tmp_path to simulate project root
        original_cwd = Path.cwd()
        try:
            Path.cwd = lambda: tmp_path

            config = DatabaseConfig("production")

            # Should create ./db directory
            expected_db_dir = tmp_path / "db"
            assert config.database_dir == expected_db_dir

            # Should use arxiv.db file
            expected_db_path = expected_db_dir / "arxiv.db"
            assert config.database_path == expected_db_path

        finally:
            # Restore original cwd function
            Path.cwd = lambda: original_cwd

    def test_testing_environment(self) -> None:
        """Test testing environment configuration."""
        config = DatabaseConfig("testing")

        # Should use /tmp directory
        assert config.database_dir == Path("/tmp")

        # Should use temporary file
        db_path = config.database_path
        assert db_path.suffix == ".db"
        assert "/tmp" in str(db_path)

    def test_connection_string(self) -> None:
        """Test connection string generation."""
        config = DatabaseConfig("testing")
        connection_string = config.get_connection_string()

        assert isinstance(connection_string, str)
        assert connection_string.endswith(".db")

    def test_setup_database_directory(self, tmp_path: Path) -> None:
        """Test database directory setup."""
        # Change to tmp_path to simulate project root
        original_cwd = Path.cwd()
        try:
            Path.cwd = lambda: tmp_path

            config = DatabaseConfig("development")
            config.setup_database_directory()

            expected_db_dir = tmp_path / "db"
            assert expected_db_dir.exists()

        finally:
            # Restore original cwd function
            Path.cwd = lambda: original_cwd

    def test_backup_path(self, tmp_path: Path) -> None:
        """Test backup path generation."""
        # Change to tmp_path to simulate project root
        original_cwd = Path.cwd()
        try:
            Path.cwd = lambda: tmp_path

            config = DatabaseConfig("development")

            # Test with custom name
            backup_path = config.get_backup_path("custom_backup.db")
            expected_backup_dir = tmp_path / "db" / "backups"
            expected_backup_path = expected_backup_dir / "custom_backup.db"
            assert backup_path == expected_backup_path

            # Test with default name (timestamp)
            backup_path = config.get_backup_path()
            assert backup_path.parent == expected_backup_dir
            assert backup_path.name.startswith("backup_")
            assert backup_path.suffix == ".db"

        finally:
            # Restore original cwd function
            Path.cwd = lambda: original_cwd

    def test_log_path(self, tmp_path: Path) -> None:
        """Test log path generation."""
        # Change to tmp_path to simulate project root
        original_cwd = Path.cwd()
        try:
            Path.cwd = lambda: tmp_path

            config = DatabaseConfig("development")
            log_path = config.get_log_path()

            expected_log_path = tmp_path / "db" / "database.log"
            assert log_path == expected_log_path

        finally:
            # Restore original cwd function
            Path.cwd = lambda: original_cwd


class TestDatabaseConfigFunctions:
    """Test database configuration convenience functions."""

    def test_get_database_path(self, tmp_path: Path) -> None:
        """Test get_database_path function."""
        # Change to tmp_path to simulate project root
        original_cwd = Path.cwd()
        try:
            Path.cwd = lambda: tmp_path

            # Test development environment
            dev_path = get_database_path("development")
            expected_dev_path = tmp_path / "db" / "arxiv.db"
            assert dev_path == expected_dev_path

            # Test testing environment
            test_path = get_database_path("testing")
            assert test_path.suffix == ".db"
            assert "/tmp" in str(test_path)

        finally:
            # Restore original cwd function
            Path.cwd = lambda: original_cwd

    def test_get_database_dir(self, tmp_path: Path) -> None:
        """Test get_database_dir function."""
        # Change to tmp_path to simulate project root
        original_cwd = Path.cwd()
        try:
            Path.cwd = lambda: tmp_path

            # Test development environment
            dev_dir = get_database_dir("development")
            expected_dev_dir = tmp_path / "db"
            assert dev_dir == expected_dev_dir

            # Test testing environment
            test_dir = get_database_dir("testing")
            assert test_dir == Path("/tmp")

        finally:
            # Restore original cwd function
            Path.cwd = lambda: original_cwd

    def test_setup_database_environment(self, tmp_path: Path) -> None:
        """Test setup_database_environment function."""
        # Change to tmp_path to simulate project root
        original_cwd = Path.cwd()
        try:
            Path.cwd = lambda: tmp_path

            # Test development environment
            config = setup_database_environment("development")
            assert config.environment == "development"

            # Should create database directory
            expected_db_dir = tmp_path / "db"
            assert expected_db_dir.exists()

        finally:
            # Restore original cwd function
            Path.cwd = lambda: original_cwd


class TestEnvironmentType:
    """Test Environment type."""

    def test_environment_values(self) -> None:
        """Test that Environment type accepts valid values."""
        # These should not raise type errors
        valid_environments: list[Environment] = [
            "development",
            "testing",
            "production",
        ]

        for env in valid_environments:
            config = DatabaseConfig(env)
            assert config.environment == env
