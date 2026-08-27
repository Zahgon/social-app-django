"""Removal of old, unused verification codes and partial pipeline data.

Replaces the ``clearsocial`` Django management command.
"""

from datetime import timedelta

from sqlalchemy import select

from .db import QuerySet, utcnow
from .models import Code, Partial


def clearsocial(age_days: int = 14) -> None:
    """Remove unused data older than ``age_days`` days."""
    age = utcnow() - timedelta(days=age_days)

    # Delete old not verified codes
    QuerySet(select(Code).where(Code.verified.is_(False), Code.timestamp < age)).delete()

    # Delete old partial data
    QuerySet(select(Partial).where(Partial.timestamp < age)).delete()


def register_cli(app) -> None:
    """Expose ``clearsocial`` as a Flask CLI command on the given app."""

    @app.cli.command("clearsocial")
    def clearsocial_command() -> None:
        """Remove old not used verification codes and partials."""
        clearsocial()
