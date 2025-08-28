"""Database utilities for common operations."""

from typing import Any, TypeVar

from pydantic import BaseModel

from core.models.database.entities import FromTupleMixinBase
from core.types import DatabaseParamType, RepositoryRowType

T = TypeVar("T", bound=BaseModel)


def row_to_model(model_class: type[T], row: RepositoryRowType) -> T:
    """Convert database row to Pydantic model.

    Args:
        model_class: The Pydantic model class to convert to
        row: Database row as dict or tuple

    Returns:
        Instance of the Pydantic model

    Raises:
        ValueError: If row type is not supported
    """
    if isinstance(row, dict):
        return model_class.model_validate(row)

    if not isinstance(row, tuple):
        raise ValueError(f"Unsupported row type: {type(row)}")

    if issubclass(model_class, FromTupleMixinBase):
        return model_class.from_tuple(row)

    field_names = list(model_class.model_fields.keys())
    if len(field_names) != len(row):
        raise ValueError(
            f"Tuple length ({len(row)}) doesn't match model fields "
            f"({len(field_names)})"
        )
    return model_class.model_validate(dict(zip(field_names, row, strict=False)))


def model_to_row(model: BaseModel) -> tuple[Any, ...]:
    """Convert Pydantic model to database row tuple.

    Args:
        model: Pydantic model instance

    Returns:
        Tuple representation of the model
    """
    return tuple(model.model_dump().values())


def safe_bind_params(
    query: str, params: DatabaseParamType
) -> tuple[str, DatabaseParamType]:
    """Safely bind parameters to SQL query.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Tuple of (query, normalized_params)

    Raises:
        ValueError: If params type is not supported
    """
    if params is None:
        return query, ()

    if isinstance(params, (list, tuple, dict)):
        return query, params

    raise ValueError(f"Unsupported params type: {type(params)}")


def build_where_clause(conditions: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Build WHERE clause from conditions dictionary.

    Args:
        conditions: Dictionary of field-value pairs for WHERE conditions

    Returns:
        Tuple of (where_clause, parameters_dict)

    Example:
        >>> build_where_clause({"name": "John", "age": 30})
        ("WHERE name = :param_name AND age = :param_age",
         {"param_name": "John", "param_age": 30})
    """
    if not conditions:
        return "", {}

    clauses: list[str] = []
    params: dict[str, Any] = {}

    for field, value in conditions.items():
        param_name = f"param_{field}"
        clauses.append(f"{field} = :{param_name}")
        params[param_name] = value

    where_clause = " AND ".join(clauses)
    return f"WHERE {where_clause}", params


def build_order_by_clause(order_by: list[str] | None) -> str:
    """Build ORDER BY clause from field list.

    Args:
        order_by: List of field names to order by

    Returns:
        ORDER BY clause string

    Example:
        >>> build_order_by_clause(["name", "age DESC"])
        "ORDER BY name, age DESC"
    """
    if not order_by:
        return ""

    return f"ORDER BY {', '.join(order_by)}"


def build_limit_clause(limit: int | None, offset: int | None = None) -> str:
    """Build LIMIT clause with optional OFFSET.

    Args:
        limit: Maximum number of rows to return
        offset: Number of rows to skip

    Returns:
        LIMIT clause string

    Example:
        >>> build_limit_clause(10, 20)
        "LIMIT 10 OFFSET 20"
    """
    if limit is None:
        return ""

    clause = f"LIMIT {limit}"
    if offset is not None:
        clause += f" OFFSET {offset}"

    return clause
