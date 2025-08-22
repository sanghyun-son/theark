"""Unit tests for repository layer."""

import pytest

from crawler.database.models import (
    AppUser,
    CrawlEvent,
    FeedItem,
    Summary,
    UserInterest,
    UserStar,
)


class TestPaperRepository:
    """Test PaperRepository."""

    def test_create_and_get_paper(self, paper_repo, sample_paper) -> None:
        """Test creating and retrieving a paper."""
        paper_id = paper_repo.create(sample_paper)
        assert paper_id > 0

        retrieved = paper_repo.get_by_arxiv_id("2101.00001")
        assert retrieved is not None
        assert retrieved.arxiv_id == "2101.00001"
        assert retrieved.title == "Test Paper"
        assert retrieved.paper_id == paper_id

    def test_get_nonexistent_paper(self, paper_repo) -> None:
        """Test retrieving a non-existent paper."""
        result = paper_repo.get_by_arxiv_id("nonexistent")
        assert result is None

    def test_update_paper(self, paper_repo, sample_paper) -> None:
        """Test updating a paper."""
        paper_id = paper_repo.create(sample_paper)
        sample_paper.paper_id = paper_id

        # Update paper
        sample_paper.title = "Updated Title"
        sample_paper.abstract = "Updated abstract"
        sample_paper.updated_at = "2021-01-02T00:00:00Z"

        success = paper_repo.update(sample_paper)
        assert success is True

        # Verify update
        retrieved = paper_repo.get_by_arxiv_id("2101.00001")
        assert retrieved is not None
        assert retrieved.title == "Updated Title"
        assert retrieved.abstract == "Updated abstract"

    def test_search_by_keywords(self, paper_repo, sample_papers) -> None:
        """Test searching papers by keywords."""
        for paper in sample_papers:
            paper_repo.create(paper)

        results = paper_repo.search_by_keywords("machine learning")
        assert len(results) >= 1
        assert any("Machine Learning" in paper.title for paper in results)

    def test_get_recent_papers(self, paper_repo, sample_papers) -> None:
        """Test getting recent papers."""
        for paper in sample_papers:
            paper_repo.create(paper)

        recent = paper_repo.get_recent_papers(limit=10)
        assert len(recent) == 2
        # Should be ordered by published_at DESC
        assert recent[0].arxiv_id == "2101.00002"  # More recent
        assert recent[1].arxiv_id == "2101.00001"  # Less recent


class TestSummaryRepository:
    """Test SummaryRepository."""

    def test_create_and_get_summary(
        self, summary_repo, paper_repo, sample_paper
    ) -> None:
        """Test creating and retrieving a summary."""
        paper_id = paper_repo.create(sample_paper)

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

        retrieved = summary_repo.get_by_paper_and_language(paper_id, "English")
        assert retrieved is not None
        assert retrieved.overview == "This paper presents a novel approach"
        assert retrieved.language == "English"
        assert retrieved.relevance == 8
        assert retrieved.model == "gpt-4"


class TestUserRepository:
    """Test UserRepository."""

    def test_create_and_get_user(self, user_repo) -> None:
        """Test creating and retrieving a user."""
        user = AppUser(email="test@example.com", display_name="Test User")
        user_id = user_repo.create_user(user)
        assert user_id > 0

        retrieved = user_repo.get_user_by_email("test@example.com")
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.display_name == "Test User"
        assert retrieved.user_id == user_id

    def test_user_interests(self, user_repo) -> None:
        """Test user interest operations."""
        user = AppUser(email="test@example.com", display_name="Test User")
        user_id = user_repo.create_user(user)

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

        retrieved = user_repo.get_user_interests(user_id)
        assert len(retrieved) == 3

        category_interest = next(i for i in retrieved if i.kind == "category")
        assert category_interest.value == "cs.CL"
        assert category_interest.weight == 2.0

    def test_user_stars(self, user_repo, paper_repo, sample_paper) -> None:
        """Test user star operations."""
        user = AppUser(email="test@example.com", display_name="Test User")
        user_id = user_repo.create_user(user)
        paper_id = paper_repo.create(sample_paper)

        star = UserStar(
            user_id=user_id, paper_id=paper_id, note="Interesting paper"
        )
        user_repo.add_star(star)

        stars = user_repo.get_user_stars(user_id)
        assert len(stars) == 1
        assert stars[0].paper_id == paper_id
        assert stars[0].note == "Interesting paper"


class TestFeedRepository:
    """Test FeedRepository."""

    def test_feed_operations(
        self, feed_repo, user_repo, paper_repo, sample_paper
    ) -> None:
        """Test feed operations."""
        user = AppUser(email="test@example.com", display_name="Test User")
        user_id = user_repo.create_user(user)
        paper_id = paper_repo.create(sample_paper)

        feed_item = FeedItem(
            user_id=user_id,
            paper_id=paper_id,
            score=0.85,
            feed_date="2021-01-01",
        )

        feed_id = feed_repo.add_feed_item(feed_item)
        assert feed_id > 0

        feed_items = feed_repo.get_user_feed(user_id, "2021-01-01")
        assert len(feed_items) == 1
        assert feed_items[0].score == 0.85
        assert feed_items[0].paper_id == paper_id


class TestCrawlEventRepository:
    """Test CrawlEventRepository."""

    def test_crawl_event_operations(self, event_repo) -> None:
        """Test crawl event operations."""
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

        recent_events = event_repo.get_recent_events(limit=10)
        assert len(recent_events) == 3

        event_types = [event.event_type for event in recent_events]
        assert "FOUND" in event_types
        assert "UPDATED" in event_types
        assert "SKIPPED" in event_types
