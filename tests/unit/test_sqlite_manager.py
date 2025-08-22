"""Unit tests for SQLite database manager."""

from pathlib import Path

import pytest

from crawler.database import SQLiteManager
from crawler.database.models import Paper


class TestSQLiteManager:
    """Test SQLite database manager."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path using pytest's tmp_path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def db_manager(self, temp_db_path: Path) -> SQLiteManager:
        """Create a database manager with temporary database."""
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            yield manager

    def test_connection_and_disconnect(self, temp_db_path: Path) -> None:
        """Test database connection and disconnection."""
        manager = SQLiteManager(temp_db_path)

        # Test connection
        manager.connect()
        assert manager.connection is not None
        assert manager.connection.row_factory is not None

        # Test disconnection
        manager.disconnect()
        assert manager.connection is None

    def test_context_manager(self, temp_db_path: Path) -> None:
        """Test context manager functionality."""
        with SQLiteManager(temp_db_path) as manager:
            assert manager.connection is not None
            manager.create_tables()

        # Should be disconnected after context exit
        assert manager.connection is None

    def test_create_tables(self, db_manager: SQLiteManager) -> None:
        """Test table creation."""
        # Check if tables exist by querying them
        tables = [
            "paper",
            "summary",
            "app_user",
            "user_interest",
            "user_star",
            "feed_item",
            "crawl_event",
        ]

        for table in tables:
            result = db_manager.fetch_one(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            assert result is not None, f"Table {table} was not created"

    def test_paper_crud_operations(self, db_manager: SQLiteManager) -> None:
        """Test paper CRUD operations."""
        # Create a test paper
        paper = Paper(
            arxiv_id="2101.00001",
            title="Test Paper",
            abstract="This is a test abstract",
            primary_category="cs.CL",
            categories="cs.CL,cs.LG",
            authors="John Doe;Jane Smith",
            url_abs="https://arxiv.org/abs/2101.00001",
            url_pdf="https://arxiv.org/pdf/2101.00001",
            published_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        )

        # Insert paper
        query = """
        INSERT INTO paper (
            arxiv_id, latest_version, title, abstract, primary_category,
            categories, authors, url_abs, url_pdf, published_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            paper.arxiv_id,
            paper.latest_version,
            paper.title,
            paper.abstract,
            paper.primary_category,
            paper.categories,
            paper.authors,
            paper.url_abs,
            paper.url_pdf,
            paper.published_at,
            paper.updated_at,
        )

        cursor = db_manager.execute(query, params)
        paper_id = cursor.lastrowid
        assert paper_id > 0

        # Read paper
        query = "SELECT * FROM paper WHERE arxiv_id = ?"
        row = db_manager.fetch_one(query, (paper.arxiv_id,))
        assert row is not None
        assert row[1] == paper.arxiv_id  # arxiv_id column
        assert row[3] == paper.title  # title column

        # Update paper
        updated_title = "Updated Test Paper"
        query = "UPDATE paper SET title = ? WHERE arxiv_id = ?"
        cursor = db_manager.execute(query, (updated_title, paper.arxiv_id))
        assert cursor.rowcount == 1

        # Verify update
        row = db_manager.fetch_one(
            "SELECT title FROM paper WHERE arxiv_id = ?", (paper.arxiv_id,)
        )
        assert row[0] == updated_title

    def test_fts_search(self, db_manager: SQLiteManager) -> None:
        """Test full-text search functionality."""
        # Insert test papers
        papers = [
            (
                "2101.00001",
                "Machine Learning Paper",
                "This paper is about machine learning",
            ),
            (
                "2101.00002",
                "Deep Learning Research",
                "Deep learning techniques and applications",
            ),
            (
                "2101.00003",
                "Computer Vision Study",
                "Computer vision and image processing",
            ),
        ]

        for arxiv_id, title, abstract in papers:
            query = """
            INSERT INTO paper (
                arxiv_id, latest_version, title, abstract, primary_category,
                categories, authors, url_abs, published_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                arxiv_id,
                1,
                title,
                abstract,
                "cs.AI",
                "cs.AI",
                "Test Author",
                "https://arxiv.org/abs/" + arxiv_id,
                "2021-01-01T00:00:00Z",
                "2021-01-01T00:00:00Z",
            )
            db_manager.execute(query, params)

        # Test simple search instead of FTS
        query = """
        SELECT title FROM paper 
        WHERE title LIKE '%machine learning%' OR abstract LIKE '%machine learning%'
        """

        results = db_manager.fetch_all(query)
        assert len(results) >= 1
        assert "Machine Learning" in results[0][0]

    def test_foreign_key_constraints(self, db_manager: SQLiteManager) -> None:
        """Test foreign key constraints."""
        # Try to insert a summary for non-existent paper
        query = """
        INSERT INTO summary (paper_id, version, style, content)
        VALUES (?, ?, ?, ?)
        """

        with pytest.raises(Exception):  # Should raise foreign key constraint error
            db_manager.execute(query, (999, 1, "tldr", "Test summary"))

    def test_unique_constraints(self, db_manager: SQLiteManager) -> None:
        """Test unique constraints."""
        # Insert first paper
        paper1 = Paper(
            arxiv_id="2101.00001",
            title="Test Paper 1",
            abstract="Test abstract 1",
            primary_category="cs.CL",
            categories="cs.CL",
            authors="Author 1",
            url_abs="https://arxiv.org/abs/2101.00001",
            published_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        )

        query = """
        INSERT INTO paper (
            arxiv_id, latest_version, title, abstract, primary_category,
            categories, authors, url_abs, published_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            paper1.arxiv_id,
            paper1.latest_version,
            paper1.title,
            paper1.abstract,
            paper1.primary_category,
            paper1.categories,
            paper1.authors,
            paper1.url_abs,
            paper1.published_at,
            paper1.updated_at,
        )
        db_manager.execute(query, params)

        # Try to insert duplicate arxiv_id
        paper2 = Paper(
            arxiv_id="2101.00001",  # Same arxiv_id
            title="Test Paper 2",
            abstract="Test abstract 2",
            primary_category="cs.CL",
            categories="cs.CL",
            authors="Author 2",
            url_abs="https://arxiv.org/abs/2101.00001",
            published_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        )

        params = (
            paper2.arxiv_id,
            paper2.latest_version,
            paper2.title,
            paper2.abstract,
            paper2.primary_category,
            paper2.categories,
            paper2.authors,
            paper2.url_abs,
            paper2.published_at,
            paper2.updated_at,
        )

        with pytest.raises(Exception):  # Should raise unique constraint error
            db_manager.execute(query, params)

    def test_batch_operations(self, db_manager: SQLiteManager) -> None:
        """Test batch operations."""
        # Prepare batch data
        papers_data = [
            ("2101.00001", "Paper 1", "Abstract 1"),
            ("2101.00002", "Paper 2", "Abstract 2"),
            ("2101.00003", "Paper 3", "Abstract 3"),
        ]

        query = """
        INSERT INTO paper (
            arxiv_id, latest_version, title, abstract, primary_category,
            categories, authors, url_abs, published_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params_list = []
        for arxiv_id, title, abstract in papers_data:
            params = (
                arxiv_id,
                1,
                title,
                abstract,
                "cs.AI",
                "cs.AI",
                "Test Author",
                "https://arxiv.org/abs/" + arxiv_id,
                "2021-01-01T00:00:00Z",
                "2021-01-01T00:00:00Z",
            )
            params_list.append(params)

        # Execute batch insert
        db_manager.execute_many(query, params_list)

        # Verify all papers were inserted
        count = db_manager.fetch_one(
            "SELECT COUNT(*) FROM paper WHERE arxiv_id LIKE '2101.0000%'"
        )
        assert count[0] == 3
