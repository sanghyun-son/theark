"""Unit tests for database models."""

import pytest
from pydantic import ValidationError

from core.models.database.entities import (
    CrawlEvent,
    FeedItem,
    PaperEntity,
    SummaryEntity,
)
from core.models.domain.user import User, UserInterest, UserStar


class TestPaper:
    """Test Paper model validation."""

    def test_valid_paper(self) -> None:
        """Test creating a valid paper."""
        paper = PaperEntity(
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

    def test_invalid_validation(self) -> None:
        """Test invalid field validation."""
        # Test invalid arXiv ID
        with pytest.raises(ValidationError, match="Invalid arXiv ID format"):
            PaperEntity(
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

        # Test invalid category
        with pytest.raises(ValidationError, match="Invalid category format"):
            PaperEntity(
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

        # Test invalid datetime
        with pytest.raises(ValidationError, match="Invalid ISO8601 datetime format"):
            PaperEntity(
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
        summary = SummaryEntity(
            paper_id=1,
            version=1,
            overview="This paper presents a novel approach",
            motivation="Current methods have limitations",
            method="We propose a new neural network",
            result="Our method achieves state-of-the-art results",
            conclusion="This work opens new research directions",
            language="English",
            interests="machine learning,neural networks,nlp",
            relevance=8,
            model="gpt-4",
        )

        assert summary.paper_id == 1
        assert summary.language == "English"
        assert summary.relevance == 8
        assert summary.model == "gpt-4"
        assert summary.is_read is False  # Default value

    def test_summary_with_read_status(self) -> None:
        """Test creating a summary with read status."""
        summary = SummaryEntity(
            paper_id=1,
            version=1,
            overview="This paper presents a novel approach",
            motivation="Current methods have limitations",
            method="We propose a new neural network",
            result="Our method achieves state-of-the-art results",
            conclusion="This work opens new research directions",
            language="English",
            interests="machine learning,neural networks,nlp",
            relevance=8,
            model="gpt-4",
            is_read=True,
        )

        assert summary.is_read is True

    def test_invalid_validation(self) -> None:
        """Test invalid field validation."""
        # Test invalid language
        with pytest.raises(ValidationError, match="Invalid language"):
            SummaryEntity(
                paper_id=1,
                version=1,
                overview="Overview",
                motivation="Motivation",
                method="Method",
                result="Result",
                conclusion="Conclusion",
                language="Spanish",
                interests="ai",
                relevance=5,
            )

        # Test invalid relevance
        with pytest.raises(ValidationError):
            SummaryEntity(
                paper_id=1,
                version=1,
                overview="Overview",
                motivation="Motivation",
                method="Method",
                result="Result",
                conclusion="Conclusion",
                language="English",
                interests="ai",
                relevance=11,  # > 10
            )


class TestAppUser:
    """Test AppUser model validation."""

    def test_valid_user(self) -> None:
        """Test creating a valid user."""
        user = User(
            email="test@example.com",
            display_name="Test User",
        )

        assert user.email == "test@example.com"
        assert user.display_name == "Test User"

    def test_invalid_email(self) -> None:
        """Test invalid email validation."""
        with pytest.raises(ValidationError, match="Invalid email format"):
            User(email="invalid-email")

    def test_email_normalization(self) -> None:
        """Test email normalization to lowercase."""
        user = User(email="TEST@EXAMPLE.COM")
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

    def test_invalid_validation(self) -> None:
        """Test invalid field validation."""
        # Test invalid kind
        with pytest.raises(ValidationError, match="Invalid kind"):
            UserInterest(
                user_id=1,
                kind="invalid",
                value="test",
            )

        # Test weight bounds
        interest = UserInterest(user_id=1, kind="category", value="test", weight=0.0)
        assert interest.weight == 0.0

        interest = UserInterest(user_id=1, kind="category", value="test", weight=10.0)
        assert interest.weight == 10.0

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
