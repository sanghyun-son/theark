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


@pytest.fixture
def mock_cwd(tmp_path: Path):
    """Mock current working directory for testing."""
    original_cwd = Path.cwd
    Path.cwd = lambda: tmp_path
    yield tmp_path
    Path.cwd = lambda: original_cwd


class TestDatabaseConfig:
    """Test DatabaseConfig class."""

    def test_development_environment(self, mock_cwd: Path) -> None:
        """Test development environment configuration."""
        config = DatabaseConfig("development")

        # Should create ./db directory
        expected_db_dir = mock_cwd / "db"
        assert config.database_dir == expected_db_dir

        # Should use arxiv.dev.db file
        expected_db_path = expected_db_dir / "arxiv.dev.db"
        assert config.database_path == expected_db_path

        # Should create directory when accessed
        config.database_path
        assert expected_db_dir.exists()

    def test_production_environment(self, mock_cwd: Path) -> None:
        """Test production environment configuration."""
        config = DatabaseConfig("production")

        # Should create ./db directory
        expected_db_dir = mock_cwd / "db"
        assert config.database_dir == expected_db_dir

        # Should use arxiv.db file
        expected_db_path = expected_db_dir / "arxiv.db"
        assert config.database_path == expected_db_path

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

    def test_setup_database_directory(self, mock_cwd: Path) -> None:
        """Test database directory setup."""
        config = DatabaseConfig("development")
        config.setup_database_directory()

        expected_db_dir = mock_cwd / "db"
        assert expected_db_dir.exists()

    def test_backup_and_log_paths(self, mock_cwd: Path) -> None:
        """Test backup and log path generation."""
        config = DatabaseConfig("development")

        # Test backup path
        backup_path = config.get_backup_path("custom_backup.db")
        expected_backup_dir = mock_cwd / "db" / "backups"
        expected_backup_path = expected_backup_dir / "custom_backup.db"
        assert backup_path == expected_backup_path

        # Test log path
        log_path = config.get_log_path()
        expected_log_path = mock_cwd / "db" / "database.log"
        assert log_path == expected_log_path


class TestDatabaseConfigFunctions:
    """Test database configuration convenience functions."""

    def test_get_database_path(self, mock_cwd: Path) -> None:
        """Test get_database_path function."""
        # Test development environment
        dev_path = get_database_path("development")
        expected_dev_path = mock_cwd / "db" / "arxiv.dev.db"
        assert dev_path == expected_dev_path

        # Test testing environment
        test_path = get_database_path("testing")
        assert test_path.suffix == ".db"
        assert "/tmp" in str(test_path)

    def test_get_database_dir(self, mock_cwd: Path) -> None:
        """Test get_database_dir function."""
        # Test development environment
        dev_dir = get_database_dir("development")
        expected_dev_dir = mock_cwd / "db"
        assert dev_dir == expected_dev_dir

        # Test testing environment
        test_dir = get_database_dir("testing")
        assert test_dir == Path("/tmp")

    def test_setup_database_environment(self, mock_cwd: Path) -> None:
        """Test setup_database_environment function."""
        config = setup_database_environment("development")
        assert config.environment == "development"

        # Should create database directory
        expected_db_dir = mock_cwd / "db"
        assert expected_db_dir.exists()


class TestEnvironmentType:
    """Test Environment type."""

    def test_environment_values(self) -> None:
        """Test that Environment type accepts valid values."""
        valid_environments: list[Environment] = [
            "development",
            "testing",
            "production",
        ]

        for env in valid_environments:
            config = DatabaseConfig(env)
            assert config.environment == env
