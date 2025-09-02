"""Base repository with dependency injection pattern."""

from typing import Generic, TypeVar

from sqlmodel import Session, SQLModel, select

from core.log import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """Base repository with dependency injection pattern."""

    def __init__(self, model: type[T], db: Session) -> None:
        self.model = model
        self.db = db

    def create(self, obj: T) -> T:
        try:
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            logger.debug(f"Created {obj.model_dump()}")
        except Exception as exc:
            self.db.rollback()
            logger.error(f"Failed to create {obj.model_dump()}: {exc}")
            raise

        return obj

    def get_by_id(self, obj_id: int) -> T | None:
        # Get the primary key field name
        pk_field = None
        for field_name, field in self.model.model_fields.items():
            if (
                field.json_schema_extra
                and isinstance(field.json_schema_extra, dict)
                and field.json_schema_extra.get("primary_key")
            ):
                pk_field = field_name
                break

        if not pk_field:
            # Fallback to common primary key names
            for name in ["id", f"{self.model.__name__.lower()}_id"]:
                if hasattr(self.model, name):
                    pk_field = name
                    break

        if not pk_field:
            raise ValueError(f"No primary key found for model {self.model.__name__}")

        statement = select(self.model).where(getattr(self.model, pk_field) == obj_id)
        result = self.db.exec(statement)
        return result.first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Get all objects with pagination."""
        statement = select(self.model).offset(skip).limit(limit)
        result = self.db.exec(statement)
        return list(result.all())

    def update(self, obj: T) -> T:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj_id: int) -> bool:
        """Delete an object by ID."""
        # Get the primary key field name
        pk_field = None
        for field_name, field in self.model.model_fields.items():
            if (
                field.json_schema_extra
                and isinstance(field.json_schema_extra, dict)
                and field.json_schema_extra.get("primary_key")
            ):
                pk_field = field_name
                break

        if not pk_field:
            # Fallback to common primary key names
            for name in ["id", f"{self.model.__name__.lower()}_id"]:
                if hasattr(self.model, name):
                    pk_field = name
                    break

        if not pk_field:
            raise ValueError(f"No primary key found for model {self.model.__name__}")

        statement = select(self.model).where(getattr(self.model, pk_field) == obj_id)
        result = self.db.exec(statement)
        obj = result.first()

        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True

        return False

    def count(self) -> int:
        """Count all objects."""
        statement = select(self.model)
        result = self.db.exec(statement)
        return len(list(result.all()))
