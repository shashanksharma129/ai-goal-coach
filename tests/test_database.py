# ABOUTME: Pytest tests for Goal SQLModel and in-memory SQLite session.
# ABOUTME: Verifies create, save, and read of Goal records.

import pytest
from uuid import uuid4

from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from database import Goal


@pytest.fixture
def in_memory_engine():
    """Engine for in-memory SQLite; one DB per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(in_memory_engine):
    """Yield a session that uses the in-memory engine."""
    with Session(in_memory_engine) as session:
        yield session


def test_goal_create_save_and_retrieve(session):
    """Create a Goal, save it, and read it back from the DB."""
    goal_id = uuid4()
    goal = Goal(
        id=goal_id,
        original_input="I want to get better at public speaking.",
        refined_goal="Improve public speaking skills by delivering 2 talks per quarter.",
        key_results='["Deliver 2 talks", "Join Toastmasters", "Practice weekly"]',
        confidence_score=0.85,
        status="draft",
    )
    session.add(goal)
    session.commit()
    session.refresh(goal)

    read = session.get(Goal, goal_id)
    assert read is not None
    assert read.id == goal_id
    assert read.original_input == "I want to get better at public speaking."
    assert read.refined_goal == "Improve public speaking skills by delivering 2 talks per quarter."
    assert read.confidence_score == 0.85
    assert read.status == "draft"
