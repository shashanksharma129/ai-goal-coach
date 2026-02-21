# ABOUTME: SQLModel Goal table and SQLite session factory.
# ABOUTME: get_session yields a session; create_all initializes the schema.

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, Session, SQLModel, create_engine

_db_path = os.environ.get("GOALS_DB_PATH", "goals.db")


class Goal(SQLModel, table=True):
    """Persisted goal record (refined goal + metadata)."""

    __tablename__ = "goals"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    original_input: str
    refined_goal: str
    key_results: str  # JSON array of strings
    confidence_score: float
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_engine = create_engine(
    f"sqlite:///{_db_path}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create all tables if they do not exist."""
    SQLModel.metadata.create_all(_engine)


@contextmanager
def get_session():
    """Yield an SQLite session for the default engine."""
    init_db()
    with Session(_engine) as session:
        yield session
