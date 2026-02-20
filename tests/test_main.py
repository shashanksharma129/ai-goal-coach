# ABOUTME: FastAPI TestClient tests for /generate and /goals; mocks agent and DB.
# ABOUTME: Tests 200, 400 (low confidence), 502 (agent error), and goal persistence.

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from database import Goal
from main import app
from schemas import GoalModel


@pytest.fixture
def in_memory_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@patch("main.get_session")
@patch("main.generate_smart_goal")
def test_generate_success(mock_generate, mock_get_session):
    """Successful /generate returns 200 and GoalModel JSON."""
    mock_generate.return_value = GoalModel(
        refined_goal="Improve public speaking.",
        key_results=["Speak monthly", "Join Toastmasters", "Practice weekly"],
        confidence_score=0.85,
    )
    client = TestClient(app)
    resp = client.post(
        "/generate",
        json={"user_input": "I want to get better at speaking."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["refined_goal"] == "Improve public speaking."
    assert data["confidence_score"] == 0.85
    assert len(data["key_results"]) == 3


@patch("main.generate_smart_goal")
def test_generate_400_low_confidence(mock_generate):
    """When confidence_score < 0.5, /generate returns 400 with message."""
    mock_generate.return_value = GoalModel(
        refined_goal="Some goal.",
        key_results=["A", "B", "C"],
        confidence_score=0.2,
    )
    client = TestClient(app)
    resp = client.post(
        "/generate",
        json={"user_input": "something vague"},
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "Input too vague or invalid to generate a goal."


@patch("main.generate_smart_goal")
def test_generate_502_on_exception(mock_generate):
    """When generate_smart_goal raises, /generate returns 502 with message."""
    mock_generate.side_effect = ValueError("ADK failed")
    client = TestClient(app)
    resp = client.post(
        "/generate",
        json={"user_input": "anything"},
    )
    assert resp.status_code == 502
    assert resp.json()["message"] == "AI model failed to generate a valid response."


def test_post_goals_persists(in_memory_engine):
    """POST /goals saves to DB and returns the created record."""
    @contextmanager
    def fake_get_session():
        with Session(in_memory_engine) as s:
            yield s

    with patch("main.get_session", fake_get_session):
        client = TestClient(app)
        resp = client.post(
            "/goals",
            json={
                "original_input": "Read more.",
                "refined_goal": "Read 12 books per year.",
                "key_results": ["1/month", "Join club", "Track list"],
                "confidence_score": 0.9,
                "status": "saved",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["refined_goal"] == "Read 12 books per year."
    assert data["original_input"] == "Read more."
    assert "id" in data
    assert data["status"] == "saved"

    with Session(in_memory_engine) as session:
        goals = list(session.exec(select(Goal)))
        assert len(goals) == 1
        assert goals[0].refined_goal == "Read 12 books per year."
