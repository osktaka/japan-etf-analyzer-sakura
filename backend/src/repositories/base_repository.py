"""Base repository with common CRUD operations."""
from typing import Generic, List, Optional, Type, TypeVar

from src.models import db

T = TypeVar("T", bound=db.Model)


class BaseRepository(Generic[T]):
    """Base repository class with CRUD operations."""

    model: Type[T]

    def __init__(self):
        """Initialize repository."""
        if not hasattr(self, "model"):
            raise NotImplementedError("Subclass must define 'model' attribute")

    def get_by_id(self, id_value) -> Optional[T]:
        """Get entity by ID."""
        return db.session.get(self.model, id_value)

    def get_all(self) -> List[T]:
        """Get all entities."""
        return db.session.query(self.model).all()

    def create(self, entity: T) -> T:
        """Create new entity."""
        db.session.add(entity)
        db.session.commit()
        return entity

    def update(self, entity: T) -> T:
        """Update existing entity."""
        db.session.commit()
        return entity

    def delete(self, entity: T) -> None:
        """Delete entity."""
        db.session.delete(entity)
        db.session.commit()

    def save(self, entity: T) -> T:
        """Save entity (create or update)."""
        db.session.add(entity)
        db.session.commit()
        return entity

    def commit(self) -> None:
        """Commit current transaction."""
        db.session.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        db.session.rollback()
