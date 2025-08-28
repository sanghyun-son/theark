"""Tests for database utilities."""

import pytest
from pydantic import BaseModel
from typing import Any

from core.database.utils import (
    row_to_model,
    model_to_row,
    safe_bind_params,
    build_where_clause,
    build_order_by_clause,
    build_limit_clause,
)
from core.models.database.entities import FromTupleMixinBase


class SampleModel(FromTupleMixinBase):
    """Sample model for testing utilities."""

    id: int
    name: str
    email: str | None = None


class SampleModelWithoutFromTuple(BaseModel):
    """Sample model without from_tuple method."""

    id: int
    name: str
    email: str | None = None


@pytest.fixture
def sample_dict_row() -> dict[str, Any]:
    """Sample dictionary row."""
    return {"id": 1, "name": "John", "email": "john@example.com"}


@pytest.fixture
def sample_tuple_row() -> tuple[Any, ...]:
    """Sample tuple row."""
    return (1, "John", "john@example.com")


@pytest.fixture
def sample_model() -> SampleModel:
    """Sample model instance."""
    return SampleModel(id=1, name="John", email="john@example.com")


def test_row_to_model_with_dict(sample_dict_row: dict[str, Any]) -> None:
    """Test converting dict row to model."""
    result = row_to_model(SampleModel, sample_dict_row)

    assert isinstance(result, SampleModel)
    assert result.id == 1
    assert result.name == "John"
    assert result.email == "john@example.com"


def test_row_to_model_with_tuple_and_from_tuple(
    sample_tuple_row: tuple[Any, ...]
) -> None:
    """Test converting tuple row to model using from_tuple method."""
    result = row_to_model(SampleModel, sample_tuple_row)

    assert isinstance(result, SampleModel)
    assert result.id == 1
    assert result.name == "John"
    assert result.email == "john@example.com"


def test_row_to_model_with_tuple_fallback(sample_tuple_row: tuple[Any, ...]) -> None:
    """Test converting tuple row to model using fallback method."""
    result = row_to_model(SampleModelWithoutFromTuple, sample_tuple_row)

    assert isinstance(result, SampleModelWithoutFromTuple)
    assert result.id == 1
    assert result.name == "John"
    assert result.email == "john@example.com"


def test_row_to_model_with_tuple_length_mismatch() -> None:
    """Test converting tuple row with length mismatch."""
    row = (1, "John")  # Missing email field

    with pytest.raises(ValueError, match="Tuple length.*doesn't match model fields"):
        row_to_model(SampleModelWithoutFromTuple, row)


def test_row_to_model_with_unsupported_type() -> None:
    """Test converting unsupported row type."""
    row = [1, "John", "john@example.com"]  # List instead of tuple/dict

    with pytest.raises(ValueError, match="Unsupported row type"):
        row_to_model(SampleModel, row)


def test_model_to_row(sample_model: SampleModel) -> None:
    """Test converting model to row tuple."""
    result = model_to_row(sample_model)

    assert result == (1, "John", "john@example.com")


def test_model_to_row_with_none_values() -> None:
    """Test converting model with None values to row tuple."""
    model = SampleModel(id=1, name="John", email=None)
    result = model_to_row(model)

    assert result == (1, "John", None)


def test_safe_bind_params_with_none() -> None:
    """Test binding None parameters."""
    query = "SELECT * FROM users"
    result_query, result_params = safe_bind_params(query, None)

    assert result_query == query
    assert result_params == ()


def test_safe_bind_params_with_tuple() -> None:
    """Test binding tuple parameters."""
    query = "SELECT * FROM users WHERE id = ?"
    params = (1,)
    result_query, result_params = safe_bind_params(query, params)

    assert result_query == query
    assert result_params == params


def test_safe_bind_params_with_list() -> None:
    """Test binding list parameters."""
    query = "SELECT * FROM users WHERE id = ?"
    params = [1]
    result_query, result_params = safe_bind_params(query, params)

    assert result_query == query
    assert result_params == params


def test_safe_bind_params_with_dict() -> None:
    """Test binding dict parameters."""
    query = "SELECT * FROM users WHERE id = :id"
    params = {"id": 1}
    result_query, result_params = safe_bind_params(query, params)

    assert result_query == query
    assert result_params == params


def test_safe_bind_params_with_unsupported_type() -> None:
    """Test binding unsupported parameter type."""
    query = "SELECT * FROM users"
    params = "invalid"  # String instead of supported types

    with pytest.raises(ValueError, match="Unsupported params type"):
        safe_bind_params(query, params)


def test_build_where_clause_with_single_condition() -> None:
    """Test building WHERE clause with single condition."""
    conditions = {"name": "John"}
    where_clause, params = build_where_clause(conditions)

    assert where_clause == "WHERE name = :param_name"
    assert params == {"param_name": "John"}


def test_build_where_clause_with_multiple_conditions() -> None:
    """Test building WHERE clause with multiple conditions."""
    conditions = {"name": "John", "age": 30}
    where_clause, params = build_where_clause(conditions)

    assert where_clause == "WHERE name = :param_name AND age = :param_age"
    assert params == {"param_name": "John", "param_age": 30}


def test_build_where_clause_with_empty_conditions() -> None:
    """Test building WHERE clause with empty conditions."""
    conditions = {}
    where_clause, params = build_where_clause(conditions)

    assert where_clause == ""
    assert params == {}


def test_build_order_by_clause_with_single_field() -> None:
    """Test building ORDER BY clause with single field."""
    order_by = ["name"]
    result = build_order_by_clause(order_by)

    assert result == "ORDER BY name"


def test_build_order_by_clause_with_multiple_fields() -> None:
    """Test building ORDER BY clause with multiple fields."""
    order_by = ["name", "age DESC"]
    result = build_order_by_clause(order_by)

    assert result == "ORDER BY name, age DESC"


def test_build_order_by_clause_with_none() -> None:
    """Test building ORDER BY clause with None."""
    result = build_order_by_clause(None)

    assert result == ""


def test_build_order_by_clause_with_empty_list() -> None:
    """Test building ORDER BY clause with empty list."""
    result = build_order_by_clause([])

    assert result == ""


def test_build_limit_clause_with_limit_only() -> None:
    """Test building LIMIT clause with limit only."""
    result = build_limit_clause(10)

    assert result == "LIMIT 10"


def test_build_limit_clause_with_limit_and_offset() -> None:
    """Test building LIMIT clause with limit and offset."""
    result = build_limit_clause(10, 20)

    assert result == "LIMIT 10 OFFSET 20"


def test_build_limit_clause_with_none_limit() -> None:
    """Test building LIMIT clause with None limit."""
    result = build_limit_clause(None)

    assert result == ""


def test_build_limit_clause_with_none_limit_and_offset() -> None:
    """Test building LIMIT clause with None limit and offset."""
    result = build_limit_clause(None, 20)

    assert result == ""
