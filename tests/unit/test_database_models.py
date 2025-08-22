"""Unit tests for database models."""

import pytest
from pydantic import ValidationError

from crawler.database.models import (
    AppUser,
    CrawlEvent,
    FeedItem,
    Paper,
    Summary,
    UserInterest,
    UserStar,
)


class TestPaper:
    """Test Paper model validation."""

    def test_valid_paper(self) -> None:
        """Test creating a valid paper."""
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

        assert paper.arxiv_id == "2101.00001"
        assert paper.title == "Test Paper"
        assert paper.latest_version == 1

    def test_invalid_arxiv_id(self) -> None:
        """Test invalid arXiv ID validation."""
        with pytest.raises(ValidationError, match="Invalid arXiv ID format"):
            Paper(
                arxiv_id="invalid",
                title="Test Paper",
                abstract="This is a test abstract",
                primary_category="cs.CL",
                categories="cs.CL",
                authors="John Doe",
                url_abs="https://arxiv.org/abs/2101.00001",
                published_at="2021-01-01T00:00:00Z",
                updated_at="2021-01-01T00:00:00Z",
            )

    def test_invalid_category(self) -> None:
        """Test invalid category validation."""
        with pytest.raises(ValidationError, match="Invalid category format"):
            Paper(
                arxiv_id="2101.00001",
                title="Test Paper",
                abstract="This is a test abstract",
                primary_category="invalid",
                categories="cs.CL",
                authors="John Doe",
                url_abs="https://arxiv.org/abs/2101.00001",
                published_at="2021-01-01T00:00:00Z",
                updated_at="2021-01-01T00:00:00Z",
            )

    def test_invalid_datetime(self) -> None:
        """Test invalid datetime validation."""
        with pytest.raises(ValidationError, match="Invalid ISO8601 datetime format"):
            Paper(
                arxiv_id="2101.00001",
                title="Test Paper",
                abstract="This is a test abstract",
                primary_category="cs.CL",
                categories="cs.CL",
                authors="John Doe",
                url_abs="https://arxiv.org/abs/2101.00001",
                published_at="invalid-date",
                updated_at="2021-01-01T00:00:00Z",
            )


class TestSummary:
    """Test Summary model validation."""

    def test_valid_summary(self) -> None:
        """Test creating a valid summary."""
        summary = Summary(
            paper_id=1,
            version=1,
            style="tldr",
            content="This is a summary",
            model="gpt-4",
        )

        assert summary.paper_id == 1
        assert summary.style == "tldr"
        assert summary.model == "gpt-4"

    def test_invalid_style(self) -> None:
        """Test invalid style validation."""
        with pytest.raises(ValidationError, match="Invalid style"):
            Summary(
                paper_id=1,
                version=1,
                style="invalid",
                content="This is a summary",
            )


class TestAppUser:
    """Test AppUser model validation."""

    def test_valid_user(self) -> None:
        """Test creating a valid user."""
        user = AppUser(
            email="test@example.com",
            display_name="Test User",
        )

        assert user.email == "test@example.com"
        assert user.display_name == "Test User"

    def test_invalid_email(self) -> None:
        """Test invalid email validation."""
        with pytest.raises(ValidationError, match="Invalid email format"):
            AppUser(email="invalid-email")

    def test_email_normalization(self) -> None:
        """Test email normalization to lowercase."""
        user = AppUser(email="TEST@EXAMPLE.COM")
        assert user.email == "test@example.com"


class TestUserInterest:
    """Test UserInterest model validation."""

    def test_valid_interest(self) -> None:
        """Test creating a valid user interest."""
        interest = UserInterest(
            user_id=1,
            kind="category",
            value="cs.CL",
            weight=2.5,
        )

        assert interest.user_id == 1
        assert interest.kind == "category"
        assert interest.weight == 2.5

    def test_invalid_kind(self) -> None:
        """Test invalid kind validation."""
        with pytest.raises(ValidationError, match="Invalid kind"):
            UserInterest(
                user_id=1,
                kind="invalid",
                value="test",
            )

    def test_weight_bounds(self) -> None:
        """Test weight bounds validation."""
        # Test minimum weight
        interest = UserInterest(user_id=1, kind="category", value="test", weight=0.0)
        assert interest.weight == 0.0

        # Test maximum weight
        interest = UserInterest(user_id=1, kind="category", value="test", weight=10.0)
        assert interest.weight == 10.0

        # Test invalid weight
        with pytest.raises(ValidationError):
            UserInterest(user_id=1, kind="category", value="test", weight=11.0)


class TestUserStar:
    """Test UserStar model validation."""

    def test_valid_star(self) -> None:
        """Test creating a valid user star."""
        star = UserStar(
            user_id=1,
            paper_id=1,
            note="Interesting paper",
        )

        assert star.user_id == 1
        assert star.paper_id == 1
        assert star.note == "Interesting paper"


class TestFeedItem:
    """Test FeedItem model validation."""

    def test_valid_feed_item(self) -> None:
        """Test creating a valid feed item."""
        feed_item = FeedItem(
            user_id=1,
            paper_id=1,
            score=0.85,
            feed_date="2021-01-01",
        )

        assert feed_item.user_id == 1
        assert feed_item.paper_id == 1
        assert feed_item.score == 0.85
        assert feed_item.feed_date == "2021-01-01"

    def test_invalid_feed_date(self) -> None:
        """Test invalid feed date validation."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            FeedItem(
                user_id=1,
                paper_id=1,
                score=0.85,
                feed_date="invalid-date",
            )


class TestCrawlEvent:
    """Test CrawlEvent model validation."""

    def test_valid_crawl_event(self) -> None:
        """Test creating a valid crawl event."""
        event = CrawlEvent(
            arxiv_id="2101.00001",
            event_type="FOUND",
            detail="Paper found successfully",
        )

        assert event.arxiv_id == "2101.00001"
        assert event.event_type == "FOUND"
        assert event.detail == "Paper found successfully"

    def test_invalid_event_type(self) -> None:
        """Test invalid event type validation."""
        with pytest.raises(ValidationError, match="Invalid event type"):
            CrawlEvent(
                arxiv_id="2101.00001",
                event_type="INVALID",
                detail="Test",
            )
