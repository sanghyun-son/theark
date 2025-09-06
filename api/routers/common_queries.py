"""Common Query parameters for API endpoints."""

from fastapi import Query


def get_pagination_params(
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of items to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
) -> tuple[int, int]:
    """Get pagination parameters.

    Returns:
        Tuple of (limit, offset)
    """
    return limit, offset


def get_language_param(
    language: str = Query(default="Korean", description="Language for summaries"),
) -> str:
    """Get language parameter.

    Returns:
        Language string
    """
    return language


def get_paper_params(
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of papers to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of papers to skip"),
    language: str = Query(default="Korean", description="Language for summaries"),
    summaries: bool = Query(
        default=False, description="Prioritize papers by summary status"
    ),
    relevance: bool = Query(
        default=False, description="Sort papers by relevance score"
    ),
    starred: bool = Query(default=False, description="Prioritize starred papers"),
    read: bool = Query(default=False, description="Prioritize read papers"),
) -> tuple[int, int, str, bool, bool, bool, bool]:
    """Get paper-specific query parameters.

    Returns:
        Tuple of (limit, offset, language, summaries, relevance, starred, read)
    """
    return (
        limit,
        offset,
        language,
        summaries,
        relevance,
        starred,
        read,
    )


def get_enhanced_paper_params(
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of papers to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of papers to skip"),
    language: str = Query(default="Korean", description="Language for summaries"),
    prioritize_summaries: bool = Query(
        default=False, description="Prioritize papers by summary status"
    ),
    sort_by_relevance: bool = Query(
        default=False, description="Sort papers by relevance score"
    ),
    categories: str = Query(
        default=None, description="Comma-separated list of categories to filter by"
    ),
) -> tuple[int, int, str, bool, bool, list[str] | None]:
    """Get enhanced paper-specific query parameters with sorting and filtering options.

    Returns:
        Tuple of (limit, offset, language, prioritize_summaries, sort_by_relevance, categories)
    """
    # Parse categories from comma-separated string
    category_list = None
    if categories:
        category_list = [cat.strip() for cat in categories.split(",") if cat.strip()]

    return (
        limit,
        offset,
        language,
        prioritize_summaries,
        sort_by_relevance,
        category_list,
    )


def get_summary_language_param(
    language: str = Query(default="Korean", description="Language for summary"),
) -> str:
    """Get summary language parameter.

    Returns:
        Language string for summary
    """
    return language
