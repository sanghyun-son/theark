"""Tests for StarService functionality."""

import pytest
from sqlmodel import Session

from core.models.rows import Paper, User
from core.services.star_service import StarService


def test_add_star_success(
    star_service: StarService,
    saved_paper: Paper,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test successful star addition."""
    response = star_service.add_star(
        mock_db_session,
        saved_user.user_id,
        saved_paper.paper_id,
        note="Interesting paper",
    )
    assert response.success
    assert response.is_starred


def test_add_star_paper_not_found(
    star_service: StarService,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test star addition with non-existent paper."""

    with pytest.raises(ValueError, match="not found"):
        star_service.add_star(
            mock_db_session,
            saved_user.user_id,
            999,
            note="Interesting paper",
        )


def test_add_star_user_not_found(
    star_service: StarService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test star addition with non-existent paper."""

    with pytest.raises(ValueError, match="not found"):
        star_service.add_star(
            mock_db_session,
            999,
            saved_paper.paper_id,
        )


def test_remove_star_success(
    star_service: StarService,
    saved_paper: Paper,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test successful star removal."""
    star_service.add_star(
        mock_db_session,
        saved_user.user_id,
        saved_paper.paper_id,
        note="Interesting paper",
    )
    response = star_service.remove_star(
        mock_db_session,
        saved_user.user_id,
        saved_paper.paper_id,
    )
    assert response.success
    assert not response.is_starred
    assert "unstarred" in response.message


def test_remove_star_paper_not_found(
    star_service: StarService,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test star addition with non-existent paper."""

    with pytest.raises(ValueError, match="not found"):
        star_service.remove_star(
            mock_db_session,
            saved_user.user_id,
            999,
        )


def test_remove_star_user_not_found(
    star_service: StarService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test star addition with non-existent paper."""
    with pytest.raises(ValueError, match="not found"):
        star_service.remove_star(
            mock_db_session,
            999,
            saved_paper.paper_id,
        )
