"""Unit tests for repository layer."""

from pathlib import Path

import pytest

from crawler.database import SQLiteManager
from crawler.database.models import (
    AppUser,
    CrawlEvent,
    FeedItem,
    Paper,
    Summary,
    UserInterest,
    UserStar,
)
from crawler.database.repository import (
    CrawlEventRepository,
    FeedRepository,
    PaperRepository,
    SummaryRepository,
    UserRepository,
)


class TestPaperRepository:
    """Test PaperRepository."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path using pytest's tmp_path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def paper_repo(self, temp_db_path: Path) -> PaperRepository:
        """Create a paper repository with temporary database."""
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            yield PaperRepository(manager)

    def test_create_and_get_paper(self, paper_repo: PaperRepository) -> None:
        """Test creating and retrieving a paper."""
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

        # Create paper
        paper_id = paper_repo.create(paper)
        assert paper_id > 0

        # Retrieve paper
        retrieved = paper_repo.get_by_arxiv_id("2101.00001")
        assert retrieved is not None
        assert retrieved.arxiv_id == "2101.00001"
        assert retrieved.title == "Test Paper"
        assert retrieved.paper_id == paper_id

    def test_get_nonexistent_paper(self, paper_repo: PaperRepository) -> None:
        """Test retrieving a non-existent paper."""
        result = paper_repo.get_by_arxiv_id("nonexistent")
        assert result is None

    def test_update_paper(self, paper_repo: PaperRepository) -> None:
        """Test updating a paper."""
        # Create paper
        paper = Paper(
            arxiv_id="2101.00001",
            title="Original Title",
            abstract="Original abstract",
            primary_category="cs.CL",
            categories="cs.CL",
            authors="Original Author",
            url_abs="https://arxiv.org/abs/2101.00001",
            published_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        )

        paper_id = paper_repo.create(paper)
        paper.paper_id = paper_id

        # Update paper
        paper.title = "Updated Title"
        paper.abstract = "Updated abstract"
        paper.updated_at = "2021-01-02T00:00:00Z"

        success = paper_repo.update(paper)
        assert success is True

        # Verify update
        retrieved = paper_repo.get_by_arxiv_id("2101.00001")
        assert retrieved is not None
        assert retrieved.title == "Updated Title"
        assert retrieved.abstract == "Updated abstract"

    def test_search_by_keywords(self, paper_repo: PaperRepository) -> None:
        """Test searching papers by keywords."""
        # Create test papers
        papers = [
            Paper(
                arxiv_id="2101.00001",
                title="Machine Learning Paper",
                abstract="This paper discusses machine learning techniques",
                primary_category="cs.AI",
                categories="cs.AI",
                authors="Author 1",
                url_abs="https://arxiv.org/abs/2101.00001",
                published_at="2021-01-01T00:00:00Z",
                updated_at="2021-01-01T00:00:00Z",
            ),
            Paper(
                arxiv_id="2101.00002",
                title="Deep Learning Research",
                abstract="Deep learning applications in computer vision",
                primary_category="cs.AI",
                categories="cs.AI",
                authors="Author 2",
                url_abs="https://arxiv.org/abs/2101.00002",
                published_at="2021-01-01T00:00:00Z",
                updated_at="2021-01-01T00:00:00Z",
            ),
        ]

        for paper in papers:
            paper_repo.create(paper)

        # Search for machine learning
        results = paper_repo.search_by_keywords("machine learning")
        assert len(results) >= 1
        assert any("Machine Learning" in paper.title for paper in results)

    def test_get_recent_papers(self, paper_repo: PaperRepository) -> None:
        """Test getting recent papers."""
        # Create test papers with different dates
        papers = [
            Paper(
                arxiv_id="2101.00001",
                title="Paper 1",
                abstract="Abstract 1",
                primary_category="cs.AI",
                categories="cs.AI",
                authors="Author 1",
                url_abs="https://arxiv.org/abs/2101.00001",
                published_at="2021-01-01T00:00:00Z",
                updated_at="2021-01-01T00:00:00Z",
            ),
            Paper(
                arxiv_id="2101.00002",
                title="Paper 2",
                abstract="Abstract 2",
                primary_category="cs.AI",
                categories="cs.AI",
                authors="Author 2",
                url_abs="https://arxiv.org/abs/2101.00002",
                published_at="2021-01-02T00:00:00Z",
                updated_at="2021-01-02T00:00:00Z",
            ),
        ]

        for paper in papers:
            paper_repo.create(paper)

        # Get recent papers
        recent = paper_repo.get_recent_papers(limit=10)
        assert len(recent) == 2
        # Should be ordered by published_at DESC
        assert recent[0].arxiv_id == "2101.00002"  # More recent
        assert recent[1].arxiv_id == "2101.00001"  # Less recent


class TestSummaryRepository:
    """Test SummaryRepository."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path using pytest's tmp_path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def summary_repo(self, temp_db_path: Path) -> SummaryRepository:
        """Create a summary repository with temporary database."""
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            yield SummaryRepository(manager)

    @pytest.fixture
    def paper_repo(self, temp_db_path: Path) -> PaperRepository:
        """Create a paper repository with temporary database."""
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            yield PaperRepository(manager)

    def test_create_and_get_summary(
        self, summary_repo: SummaryRepository, paper_repo: PaperRepository
    ) -> None:
        """Test creating and retrieving a summary."""
        # Create a paper first
        paper = Paper(
            arxiv_id="2101.00001",
            title="Test Paper",
            abstract="Test abstract",
            primary_category="cs.CL",
            categories="cs.CL",
            authors="Test Author",
            url_abs="https://arxiv.org/abs/2101.00001",
            published_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        )
        paper_id = paper_repo.create(paper)

        # Create summary
        summary = Summary(
            paper_id=paper_id,
            version=1,
            overview="This paper presents a novel approach",
            motivation="Current methods have limitations",
            method="We propose a new neural network",
            result="Our method achieves state-of-the-art results",
            conclusion="This work opens new research directions",
            language="English",
            interests="machine learning,neural networks",
            relevance=8,
            model="gpt-4",
        )

        summary_id = summary_repo.create(summary)
        assert summary_id > 0

        # Retrieve summary
        retrieved = summary_repo.get_by_paper_and_language(paper_id, "English")
        assert retrieved is not None
        assert retrieved.overview == "This paper presents a novel approach"
        assert retrieved.language == "English"
        assert retrieved.relevance == 8
        assert retrieved.model == "gpt-4"


class TestUserRepository:
    """Test UserRepository."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path using pytest's tmp_path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def user_repo(self, temp_db_path: Path) -> UserRepository:
        """Create a user repository with temporary database."""
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            yield UserRepository(manager)

    def test_create_and_get_user(self, user_repo: UserRepository) -> None:
        """Test creating and retrieving a user."""
        user = AppUser(
            email="test@example.com",
            display_name="Test User",
        )

        user_id = user_repo.create_user(user)
        assert user_id > 0

        retrieved = user_repo.get_user_by_email("test@example.com")
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.display_name == "Test User"
        assert retrieved.user_id == user_id

    def test_user_interests(self, user_repo: UserRepository) -> None:
        """Test user interest operations."""
        # Create user
        user = AppUser(email="test@example.com", display_name="Test User")
        user_id = user_repo.create_user(user)

        # Add interests
        interests = [
            UserInterest(
                user_id=user_id, kind="category", value="cs.CL", weight=2.0
            ),
            UserInterest(
                user_id=user_id,
                kind="keyword",
                value="machine learning",
                weight=1.5,
            ),
            UserInterest(
                user_id=user_id, kind="author", value="John Doe", weight=1.0
            ),
        ]

        for interest in interests:
            user_repo.add_interest(interest)

        # Get interests
        retrieved = user_repo.get_user_interests(user_id)
        assert len(retrieved) == 3

        # Check specific interest
        category_interest = next(i for i in retrieved if i.kind == "category")
        assert category_interest.value == "cs.CL"
        assert category_interest.weight == 2.0

    def test_user_stars(
        self, user_repo: UserRepository, temp_db_path: Path
    ) -> None:
        """Test user star operations."""
        # Create user
        user = AppUser(email="test@example.com", display_name="Test User")
        user_id = user_repo.create_user(user)

        # Create a paper
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            paper_repo = PaperRepository(manager)
            paper = Paper(
                arxiv_id="2101.00001",
                title="Test Paper",
                abstract="Test abstract",
                primary_category="cs.CL",
                categories="cs.CL",
                authors="Test Author",
                url_abs="https://arxiv.org/abs/2101.00001",
                published_at="2021-01-01T00:00:00Z",
                updated_at="2021-01-01T00:00:00Z",
            )
            paper_id = paper_repo.create(paper)

        # Add star
        star = UserStar(
            user_id=user_id,
            paper_id=paper_id,
            note="Interesting paper",
        )
        user_repo.add_star(star)

        # Get stars
        stars = user_repo.get_user_stars(user_id)
        assert len(stars) == 1
        assert stars[0].paper_id == paper_id
        assert stars[0].note == "Interesting paper"


class TestFeedRepository:
    """Test FeedRepository."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path using pytest's tmp_path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def feed_repo(self, temp_db_path: Path) -> FeedRepository:
        """Create a feed repository with temporary database."""
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            yield FeedRepository(manager)

    def test_feed_operations(
        self, feed_repo: FeedRepository, temp_db_path: Path
    ) -> None:
        """Test feed operations."""
        # Create user and paper
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            user_repo = UserRepository(manager)
            paper_repo = PaperRepository(manager)

            user = AppUser(email="test@example.com", display_name="Test User")
            user_id = user_repo.create_user(user)

            paper = Paper(
                arxiv_id="2101.00001",
                title="Test Paper",
                abstract="Test abstract",
                primary_category="cs.CL",
                categories="cs.CL",
                authors="Test Author",
                url_abs="https://arxiv.org/abs/2101.00001",
                published_at="2021-01-01T00:00:00Z",
                updated_at="2021-01-01T00:00:00Z",
            )
            paper_id = paper_repo.create(paper)

        # Add feed item
        feed_item = FeedItem(
            user_id=user_id,
            paper_id=paper_id,
            score=0.85,
            feed_date="2021-01-01",
        )

        feed_id = feed_repo.add_feed_item(feed_item)
        assert feed_id > 0

        # Get feed
        feed_items = feed_repo.get_user_feed(user_id, "2021-01-01")
        assert len(feed_items) == 1
        assert feed_items[0].score == 0.85
        assert feed_items[0].paper_id == paper_id


class TestCrawlEventRepository:
    """Test CrawlEventRepository."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path using pytest's tmp_path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def event_repo(self, temp_db_path: Path) -> CrawlEventRepository:
        """Create a crawl event repository with temporary database."""
        manager = SQLiteManager(temp_db_path)
        with manager:
            manager.create_tables()
            yield CrawlEventRepository(manager)

    def test_crawl_event_operations(
        self, event_repo: CrawlEventRepository
    ) -> None:
        """Test crawl event operations."""
        # Log events
        events = [
            CrawlEvent(
                arxiv_id="2101.00001", event_type="FOUND", detail="Paper found"
            ),
            CrawlEvent(
                arxiv_id="2101.00002",
                event_type="UPDATED",
                detail="Paper updated",
            ),
            CrawlEvent(
                arxiv_id="2101.00003",
                event_type="SKIPPED",
                detail="Paper skipped",
            ),
        ]

        for event in events:
            event_id = event_repo.log_event(event)
            assert event_id > 0

        # Get recent events
        recent_events = event_repo.get_recent_events(limit=10)
        assert len(recent_events) == 3

        # Check event types
        event_types = [event.event_type for event in recent_events]
        assert "FOUND" in event_types
        assert "UPDATED" in event_types
        assert "SKIPPED" in event_types
