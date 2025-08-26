"""Repository for user operations."""

from core.database.interfaces import DatabaseManager
from core.models.database.entities import (
    UserEntity,
    UserInterestEntity,
    UserStarEntity,
)
from core.types import RepositoryRowType


class UserRepository:
    """Repository for user operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_user(self, row: RepositoryRowType) -> UserEntity:
        """Convert database row to AppUser model.

        Args:
            row: Database row tuple or dict

        Returns:
            AppUser model instance
        """
        if isinstance(row, dict):
            return UserEntity.model_validate(row)

        return UserEntity.from_tuple(row)

    def _row_to_interest(self, row: RepositoryRowType) -> UserInterestEntity:
        """Convert database row to UserInterest model.

        Args:
            row: Database row tuple or dict

        Returns:
            UserInterest model instance
        """
        if isinstance(row, dict):
            return UserInterestEntity.model_validate(row)

        return UserInterestEntity.from_tuple(row)

    def _row_to_star(self, row: RepositoryRowType) -> UserStarEntity:
        """Convert database row to UserStar model.

        Args:
            row: Database row tuple or dict

        Returns:
            UserStar model instance
        """
        if isinstance(row, dict):
            return UserStarEntity.model_validate(row)

        return UserStarEntity.from_tuple(row)

    async def create_user(self, user: UserEntity) -> int:
        """Create a new user.

        Args:
            user: User model instance

        Returns:
            Created user ID
        """
        query = "INSERT INTO app_user (email, display_name) VALUES (?, ?)"
        params = (user.email, user.display_name)

        cursor = await self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    async def get_user_by_email(self, email: str) -> UserEntity | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User model or None if not found
        """
        query = "SELECT * FROM app_user WHERE email = ?"
        row = await self.db.fetch_one(query, (email,))

        if row:
            return self._row_to_user(row)
        return None

    async def get_user_by_id(self, user_id: int) -> UserEntity | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User model or None if not found
        """
        query = "SELECT * FROM app_user WHERE user_id = ?"
        row = await self.db.fetch_one(query, (user_id,))

        if row:
            return self._row_to_user(row)
        return None

    async def add_interest(self, interest: UserInterestEntity) -> None:
        """Add or update user interest.

        Args:
            interest: User interest model
        """
        query = """
        INSERT OR REPLACE INTO user_interest (user_id, kind, value, weight)
        VALUES (?, ?, ?, ?)
        """
        params = (
            interest.user_id,
            interest.kind,
            interest.value,
            interest.weight,
        )
        await self.db.execute(query, params)

    async def get_user_interests(self, user_id: int) -> list[UserInterestEntity]:
        """Get all interests for a user.

        Args:
            user_id: User ID

        Returns:
            List of user interests
        """
        query = "SELECT * FROM user_interest WHERE user_id = ?"
        rows = await self.db.fetch_all(query, (user_id,))

        interests = []
        for row in rows:
            interests.append(self._row_to_interest(row))

        return interests

    async def add_star(self, star: UserStarEntity) -> None:
        """Add a star/bookmark for a user.

        Args:
            star: User star model
        """
        query = """
        INSERT OR REPLACE INTO user_star (user_id, paper_id, note)
        VALUES (?, ?, ?)
        """
        params = (star.user_id, star.paper_id, star.note)
        await self.db.execute(query, params)

    async def remove_star(self, user_id: int, paper_id: int) -> bool:
        """Remove a star/bookmark for a user.

        Args:
            user_id: User ID
            paper_id: Paper ID

        Returns:
            True if removed, False if not found
        """
        query = "DELETE FROM user_star WHERE user_id = ? AND paper_id = ?"
        cursor = await self.db.execute(query, (user_id, paper_id))
        return bool(cursor.rowcount > 0)

    async def get_user_stars(
        self, user_id: int, limit: int = 100
    ) -> list[UserStarEntity]:
        """Get all stars for a user.

        Args:
            user_id: User ID
            limit: Maximum number of results

        Returns:
            List of user stars
        """
        query = """
        SELECT * FROM user_star
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """

        rows = await self.db.fetch_all(query, (user_id, limit))
        stars = []

        for row in rows:
            stars.append(self._row_to_star(row))

        return stars
