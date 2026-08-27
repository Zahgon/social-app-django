"""Database plumbing for Social Auth on Flask.

Plain SQLAlchemy 2.0 is used (not Flask-SQLAlchemy) so that the storage
classmethods keep working outside of an application/request context, which is
what ``social-core`` expects from a storage layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Iterator

    from flask import Flask
    from sqlalchemy import Engine, Select


class Base(DeclarativeBase):
    """Declarative base shared by every Social Auth model."""


session = scoped_session(sessionmaker(future=True, expire_on_commit=False))


def utcnow() -> datetime:
    """Naive UTC timestamp, the storage format used by every timestamp column."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class QuerySet:
    """Minimal lazy result wrapper with the subset of the Django QuerySet API
    that ``social-core`` and the storage layer rely on."""

    def __init__(self, statement: Select) -> None:
        self.statement = statement

    def _rows(self) -> list[Any]:
        return list(session.scalars(self.statement))

    def __iter__(self) -> Iterator[Any]:
        return iter(self._rows())

    def __len__(self) -> int:
        return len(self._rows())

    def __getitem__(self, index):
        return self._rows()[index]

    def count(self) -> int:
        return len(self._rows())

    def first(self) -> Any:
        return session.scalars(self.statement).first()

    def exists(self) -> bool:
        return self.first() is not None

    def delete(self) -> None:
        for row in self._rows():
            session.delete(row)
        session.commit()


class SaveMixin:
    """Active-record helpers shared by the models, mirroring the Django ORM
    methods ``social-core`` calls on model instances."""

    def save(self):
        session.add(self)
        session.commit()
        return self

    def delete(self) -> None:
        session.delete(self)
        session.commit()


def init_social(app: Flask, engine: Engine) -> None:
    """Bind the shared session to ``engine`` and create the missing tables."""
    session.configure(bind=engine)
    Base.metadata.create_all(engine)
    app.extensions["social_flask_engine"] = engine
