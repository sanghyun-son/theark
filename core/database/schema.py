"""Database schema utilities."""

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class ColumnDefinition:
    """Database column definition."""

    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default: Any = None
    auto_increment: bool = False


@dataclass
class TableDefinition:
    """Database table definition."""

    name: str
    columns: Sequence[ColumnDefinition]
    indexes: Sequence[str] = field(default_factory=list)
