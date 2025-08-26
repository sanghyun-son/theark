"""Unit tests for SQLite database manager."""

import pytest

from core.models.database.entities import PaperEntity
from core.database.implementations.sqlite.sqlite_manager import SQLiteManager


@pytest.mark.asyncio
async def test_connection_and_disconnect(temp_db_path) -> None:
    """Test database connection and disconnection."""
    manager = SQLiteManager(temp_db_path)

    # Test connection
    await manager.connect()
    assert manager._connection is not None
    assert manager._connection._connection.row_factory is not None

    # Test disconnection
    await manager.disconnect()
    assert not manager.is_connected


@pytest.mark.asyncio
async def test_context_manager(temp_db_path) -> None:
    """Test context manager functionality."""
    async with SQLiteManager(temp_db_path) as manager:
        assert manager._connection is not None
        await manager.create_tables()

    # Should be disconnected after context exit
    assert not manager.is_connected


@pytest.mark.asyncio
async def test_create_tables(db_manager) -> None:
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
        "llm_tracking",
        "llm_requests",
    ]

    for table in tables:
        result = await db_manager.fetch_one(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
        )
        assert result is not None, f"Table {table} was not created"


@pytest.mark.asyncio
async def test_basic_crud_operations(db_manager, sample_paper) -> None:
    """Test basic CRUD operations."""
    # Insert paper
    query = """
    INSERT INTO paper (
        arxiv_id, latest_version, title, abstract, primary_category,
        categories, authors, url_abs, url_pdf, published_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        sample_paper.arxiv_id,
        sample_paper.latest_version,
        sample_paper.title,
        sample_paper.abstract,
        sample_paper.primary_category,
        sample_paper.categories,
        sample_paper.authors,
        sample_paper.url_abs,
        sample_paper.url_pdf,
        sample_paper.published_at,
        sample_paper.updated_at,
    )

    cursor = await db_manager.execute(query, params)
    paper_id = cursor.lastrowid
    assert paper_id > 0

    # Read paper
    query = "SELECT * FROM paper WHERE arxiv_id = ?"
    row = await db_manager.fetch_one(query, (sample_paper.arxiv_id,))
    assert row is not None
    assert row["arxiv_id"] == sample_paper.arxiv_id  # arxiv_id column
    assert row["title"] == sample_paper.title  # title column

    # Update paper
    updated_title = "Updated Test Paper"
    query = "UPDATE paper SET title = ? WHERE arxiv_id = ?"
    cursor = await db_manager.execute(query, (updated_title, sample_paper.arxiv_id))
    assert cursor.rowcount == 1

    # Verify update
    row = await db_manager.fetch_one(
        "SELECT title FROM paper WHERE arxiv_id = ?",
        (sample_paper.arxiv_id,),
    )
    assert row["title"] == updated_title


@pytest.mark.asyncio
async def test_search_functionality(db_manager, sample_papers) -> None:
    """Test search functionality."""
    # Insert test papers
    for paper in sample_papers:
        query = """
        INSERT INTO paper (
            arxiv_id, latest_version, title, abstract, primary_category,
            categories, authors, url_abs, published_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            paper.published_at,
            paper.updated_at,
        )
        await db_manager.execute(query, params)

    # Test simple search
    query = """
    SELECT title FROM paper 
    WHERE title LIKE '%machine learning%' OR abstract LIKE '%machine learning%'
    """

    results = await db_manager.fetch_all(query)
    assert len(results) >= 1
    assert "Machine Learning" in results[0]["title"]


@pytest.mark.asyncio
async def test_constraints(db_manager) -> None:
    """Test database constraints."""
    # Test foreign key constraint
    with pytest.raises(Exception):  # Should raise foreign key constraint error
        await db_manager.execute(
            "INSERT INTO summary (paper_id, version, overview, motivation, method, result, conclusion, language, interests, relevance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                999,
                1,
                "overview",
                "motivation",
                "method",
                "result",
                "conclusion",
                "English",
                "interests",
                5,
            ),
        )

    # Test unique constraint
    paper1 = PaperEntity(
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
    await db_manager.execute(query, params)

    # Try to insert duplicate arxiv_id
    paper2 = PaperEntity(
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
        await db_manager.execute(query, params)


@pytest.mark.asyncio
async def test_batch_operations(db_manager) -> None:
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
    for params in params_list:
        await db_manager.execute(query, params)

    # Verify all papers were inserted
    count = await db_manager.fetch_one(
        "SELECT COUNT(*) FROM paper WHERE arxiv_id LIKE '2101.0000%'"
    )
    assert count["COUNT(*)"] == 3
