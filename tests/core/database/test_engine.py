from core.database.engine import (
    create_database_engine,
    create_database_tables,
    drop_database_tables,
    reset_database,
)
from core.types import Environment


def test_create_database_tables() -> None:
    engine = create_database_engine(Environment.TESTING)
    assert engine is not None
    create_database_tables(engine)


def test_drop_database_tables() -> None:
    engine = create_database_engine(Environment.TESTING)
    assert engine is not None
    create_database_tables(engine)
    drop_database_tables(engine)


def test_reset_database() -> None:
    engine = create_database_engine(Environment.TESTING)
    assert engine is not None
    create_database_tables(engine)
    reset_database(engine)
