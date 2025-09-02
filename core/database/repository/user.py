"""User repository using SQLModel with dependency injection."""

from sqlmodel import Session, func, select

from core.database.repository.base import BaseRepository
from core.log import get_logger
from core.models.rows import Paper, User, UserInterest, UserStar

logger = get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """User repository using SQLModel with dependency injection."""

    def __init__(self, db: Session) -> None:
        """Initialize user repository."""
        super().__init__(User, db)

    def get_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        statement = select(User).where(User.email == email)
        result = self.db.exec(statement)
        return result.first()


class UserInterestRepository(BaseRepository[UserInterest]):
    """User interest repository using SQLModel with dependency injection."""

    def __init__(self, db: Session) -> None:
        """Initialize user interest repository."""
        super().__init__(UserInterest, db)

    def get_user_interests(self, user_id: int) -> list[UserInterest]:
        """Get user interests.

        Args:
            user_id: User ID

        Returns:
            List of user interests
        """
        statement = select(UserInterest).where(UserInterest.user_id == user_id)
        result = self.db.exec(statement)
        return list(result.all())

    def add_user_interest(
        self, user_id: int, category: str, weight: int
    ) -> UserInterest:
        """Add user interest.

        Args:
            user_id: User ID
            category: Interest category
            weight: Interest weight (1-10)

        Returns:
            Created user interest
        """
        interest = UserInterest(user_id=user_id, category=category, weight=weight)
        return self.create(interest)

    def remove_user_interest(self, user_id: int, category: str) -> bool:
        """Remove user interest.

        Args:
            user_id: User ID
            category: Interest category to remove

        Returns:
            True if removed, False if not found
        """
        statement = select(UserInterest).where(
            (UserInterest.user_id == user_id) & (UserInterest.category == category)
        )
        result = self.db.exec(statement)
        interest = result.first()

        if interest:
            self.db.delete(interest)
            self.db.commit()
            return True

        return False


class UserStarRepository(BaseRepository[UserStar]):
    """User star repository using SQLModel with dependency injection."""

    def __init__(self, db: Session) -> None:
        """Initialize user star repository."""
        super().__init__(UserStar, db)

    def get_user_stars(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[UserStar]:
        """Get user starred papers.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user stars
        """
        statement = (
            select(UserStar)
            .where(UserStar.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )

        result = self.db.exec(statement)
        return list(result.all())

    def add_user_star(
        self, user_id: int, paper_id: int, note: str | None = None
    ) -> UserStar:
        """Add user star.

        Args:
            user_id: User ID
            paper_id: Paper ID to star
            note: Optional note for the star

        Returns:
            Created user star
        """
        star = UserStar(user_id=user_id, paper_id=paper_id, note=note)
        return self.create(star)

    def remove_user_star(self, user_id: int, paper_id: int) -> bool:
        """Remove user star.

        Args:
            user_id: User ID
            paper_id: Paper ID to unstar

        Returns:
            True if removed, False if not found
        """
        statement = select(UserStar).where(
            (UserStar.user_id == user_id) & (UserStar.paper_id == paper_id)
        )
        result = self.db.exec(statement)
        star = result.first()

        if star:
            self.db.delete(star)
            self.db.commit()
            return True

        return False

    def is_paper_starred(self, user_id: int, paper_id: int) -> bool:
        """Check if paper is starred by user.

        Args:
            user_id: User ID
            paper_id: Paper ID

        Returns:
            True if starred, False otherwise
        """
        statement = select(UserStar).where(
            (UserStar.user_id == user_id) & (UserStar.paper_id == paper_id)
        )
        result = self.db.exec(statement)
        return result.first() is not None

    def get_user_star(self, user_id: int, paper_id: int) -> UserStar | None:
        """Get user star with note information.

        Args:
            user_id: User ID
            paper_id: Paper ID

        Returns:
            UserStar object if found, None otherwise
        """
        statement = select(UserStar).where(
            (UserStar.user_id == user_id) & (UserStar.paper_id == paper_id)
        )
        result = self.db.exec(statement)
        return result.first()

    def get_starred_papers_count(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(UserStar)
            .where(UserStar.user_id == user_id)
        )
        return self.db.exec(stmt).one()

    def get_starred_papers(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Paper]:
        """Get papers starred by user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of starred papers
        """
        # This would need to be implemented with a join query
        # For now, we'll get the star records and then fetch papers
        stars = self.get_user_stars(user_id, skip, limit)

        papers = []
        for star in stars:
            # Fetch the paper for each star
            paper_statement = select(Paper).where(Paper.paper_id == star.paper_id)
            paper_result = self.db.exec(paper_statement)
            paper = paper_result.first()
            if paper:
                papers.append(paper)

        return papers

    def get_starred_paper_ids(self, user_id: int, paper_ids: list[int]) -> list[int]:
        """Get list of paper IDs that are starred by user (batch operation).

        Args:
            user_id: User ID
            paper_ids: List of paper IDs to check

        Returns:
            List of paper IDs that are starred by the user
        """
        if not paper_ids:
            return []

        statement = select(UserStar.paper_id).where(
            (UserStar.user_id == user_id)
            & (UserStar.paper_id.in_(paper_ids))  # type: ignore
        )
        result = self.db.exec(statement)
        return list(result.all())
