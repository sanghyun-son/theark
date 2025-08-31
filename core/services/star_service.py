"""Service for star-related operations."""

from sqlmodel import Session

from core.database.repository import (
    PaperRepository,
    UserRepository,
    UserStarRepository,
)
from core.models import StarResponse


class StarService:
    """Service for star-related operations."""

    def _check_valid_user_and_paper(
        self,
        session: Session,
        user_id: int,
        paper_id: int,
    ) -> str:
        """Check if user and paper exist."""
        if not UserRepository(session).get_by_id(user_id):
            return f"User {user_id} not found"
        if not PaperRepository(session).get_by_id(paper_id):
            return f"Paper {paper_id} not found"
        return ""

    def add_star(
        self,
        session: Session,
        user_id: int | None,
        paper_id: int | None,
        note: str | None = None,
    ) -> StarResponse:
        """Add a star to a paper."""
        if user_id is None or paper_id is None:
            return StarResponse.failure_response("User or paper ID is None")
        if msg := self._check_valid_user_and_paper(session, user_id, paper_id):
            raise ValueError(msg)

        star_repo = UserStarRepository(session)
        if star_repo.is_paper_starred(user_id, paper_id):
            return StarResponse.failure_response(f"Paper {paper_id} is already starred")

        star_repo.add_user_star(user_id, paper_id, note)
        return StarResponse(
            success=True,
            is_starred=True,
            message="Paper starred successfully",
            paper_id=paper_id,
            note=note,
        )

    def remove_star(
        self,
        session: Session,
        user_id: int | None,
        paper_id: int | None,
    ) -> StarResponse:
        """Remove a star from a paper."""
        if user_id is None or paper_id is None:
            return StarResponse.failure_response("User or paper ID is None")
        if msg := self._check_valid_user_and_paper(session, user_id, paper_id):
            raise ValueError(msg)

        star_repo = UserStarRepository(session)
        if star_repo.remove_user_star(user_id, paper_id):
            return StarResponse(
                success=True,
                message="Paper unstarred successfully",
                is_starred=False,
                paper_id=paper_id,
                note=None,
            )

        return StarResponse.failure_response(f"Paper {paper_id} is not starred")

    def is_paper_starred(
        self,
        session: Session,
        user_id: int | None,
        paper_id: int | None,
    ) -> StarResponse:
        """Check if a paper is starred by the user."""
        if user_id is None or paper_id is None:
            return StarResponse.failure_response("User or paper ID is None")
        if msg := self._check_valid_user_and_paper(session, user_id, paper_id):
            raise ValueError(msg)

        star_repo = UserStarRepository(session)
        if star_repo.is_paper_starred(user_id, paper_id):
            star = star_repo.get_user_star(user_id, paper_id)
            return StarResponse(
                success=True,
                is_starred=True,
                message=f"Paper {paper_id} is starred",
                paper_id=paper_id,
                note=star.note if star else None,
            )
        else:
            return StarResponse(
                success=True,
                is_starred=False,
                message=f"Paper {paper_id} is not starred",
                paper_id=paper_id,
                note=None,
            )

    def is_paper_starred_by_user(
        self, session: Session, user_id: int, paper_id: int
    ) -> bool:
        """Check if a paper is starred by a user, returning a boolean."""
        return UserStarRepository(session).is_paper_starred(user_id, paper_id)
