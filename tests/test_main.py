# ABOUTME: FastAPI TestClient tests for /auth, /generate and /goals; mocks agent and DB.
# ABOUTME: Tests auth signup/login, 401 when unauthenticated, and goal persistence scoped by user.

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from api.main import app
from core.auth import create_access_token, hash_password
from core.database import Goal, User
from core.schemas import GoalModel


@pytest.fixture
def in_memory_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def fake_get_session(in_memory_engine):
    """Context manager that yields a session on the in-memory engine. Patch core.database.get_session so auth and routes use same DB."""

    @contextmanager
    def _fake():
        with Session(in_memory_engine) as s:
            yield s

    return _fake


@pytest.fixture
def auth_headers(fake_get_session, in_memory_engine):
    """Create a user in the in-memory DB and return headers with a valid Bearer token."""
    with patch("core.database.get_session", fake_get_session):
        with Session(in_memory_engine) as session:
            user = User(username="testuser", password_hash=hash_password("testpass"))
            session.add(user)
            session.commit()
            session.refresh(user)
            token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _with_fake_session(fake_get_session):
    """Patch get_session in api and auth (where it is imported) so all app code uses the in-memory DB."""

    @contextmanager
    def _both():
        with (
            patch("api.main.get_session", fake_get_session),
            patch("core.auth.get_session", fake_get_session),
        ):
            yield

    return _both()


def test_auth_signup_201_returns_id_and_username(fake_get_session, in_memory_engine):
    """POST /auth/signup with valid body returns 201 and id, username."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.post(
            "/auth/signup",
            json={"username": "newuser", "password": "password123"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert "id" in data


def test_auth_signup_409_when_username_taken(fake_get_session):
    """POST /auth/signup with existing username returns 409."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        client.post(
            "/auth/signup", json={"username": "taken", "password": "password123"}
        )
        resp = client.post(
            "/auth/signup", json={"username": "taken", "password": "other456"}
        )
    assert resp.status_code == 409
    assert "already taken" in resp.json().get("message", "").lower()


def test_auth_signup_400_when_password_too_short(fake_get_session):
    """POST /auth/signup with short password returns 400."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.post(
            "/auth/signup",
            json={"username": "u", "password": "short"},
        )
    assert resp.status_code == 400
    msg = resp.json().get("message", "")
    assert "password" in msg.lower() or "8" in msg


def test_auth_login_200_returns_token(fake_get_session, in_memory_engine):
    """POST /auth/login with valid credentials returns 200 and access_token."""
    with _with_fake_session(fake_get_session):
        with Session(in_memory_engine) as session:
            user = User(username="logintest", password_hash=hash_password("secret"))
            session.add(user)
            session.commit()
        client = TestClient(app)
        resp = client.post(
            "/auth/login",
            json={"username": "logintest", "password": "secret"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("token_type") == "bearer"
    assert "access_token" in data
    assert data.get("expires_in") > 0


def test_auth_login_401_wrong_password(fake_get_session, in_memory_engine):
    """POST /auth/login with wrong password returns 401."""
    with _with_fake_session(fake_get_session):
        with Session(in_memory_engine) as session:
            user = User(username="u2", password_hash=hash_password("right"))
            session.add(user)
            session.commit()
        client = TestClient(app)
        resp = client.post(
            "/auth/login",
            json={"username": "u2", "password": "wrong"},
        )
    assert resp.status_code == 401
    assert "message" in resp.json()


def test_generate_401_without_token(fake_get_session):
    """POST /generate without Authorization returns 401."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.post("/generate", json={"user_input": "goal"})
    assert resp.status_code == 401


def test_goals_post_401_without_token(fake_get_session):
    """POST /goals without Authorization returns 401."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.post(
            "/goals",
            json={
                "original_input": "x",
                "refined_goal": "y",
                "key_results": ["a", "b", "c"],
                "confidence_score": 0.8,
                "status": "draft",
            },
        )
    assert resp.status_code == 401


def test_goals_get_401_without_token(fake_get_session):
    """GET /goals without Authorization returns 401."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.get("/goals")
    assert resp.status_code == 401


@patch("api.main.generate_smart_goal")
def test_generate_success(mock_generate, fake_get_session, auth_headers):
    """Successful /generate with valid token returns 200 and GoalModel JSON."""
    mock_generate.return_value = GoalModel(
        refined_goal="Improve public speaking.",
        key_results=["Speak monthly", "Join Toastmasters", "Practice weekly"],
        confidence_score=0.85,
    )
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.post(
            "/generate",
            json={"user_input": "I want to get better at speaking."},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["refined_goal"] == "Improve public speaking."
    assert data["confidence_score"] == 0.85
    assert len(data["key_results"]) == 3


@patch("api.main.generate_smart_goal")
def test_generate_400_low_confidence(mock_generate, fake_get_session, auth_headers):
    """When confidence_score < 0.5, /generate returns 400 with message."""
    mock_generate.return_value = GoalModel(
        refined_goal="Some goal.",
        key_results=["A", "B", "C"],
        confidence_score=0.2,
    )
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.post(
            "/generate",
            json={"user_input": "something vague"},
            headers=auth_headers,
        )
    assert resp.status_code == 400
    assert resp.json()["message"] == "Input too vague or invalid to generate a goal."


@patch("api.main.generate_smart_goal")
def test_generate_502_on_exception(mock_generate, fake_get_session, auth_headers):
    """When generate_smart_goal raises, /generate returns 502 with message."""
    mock_generate.side_effect = ValueError("ADK failed")
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.post(
            "/generate",
            json={"user_input": "anything"},
            headers=auth_headers,
        )
    assert resp.status_code == 502
    assert resp.json()["message"] == "AI model failed to generate a valid response."


def test_post_goals_persists(fake_get_session, in_memory_engine, auth_headers):
    """POST /goals with auth saves to DB and returns the created record; GET returns only that user's goals."""
    with _with_fake_session(fake_get_session):
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
            headers=auth_headers,
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
        assert goals[0].user_id is not None


def test_get_goals_empty_returns_200_and_empty_list(fake_get_session, auth_headers):
    """GET /goals with no goals for user returns 200 and { goals: [], total: 0 }."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.get("/goals", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["goals"] == []
    assert data["total"] == 0


def test_get_goals_returns_newest_first_with_pagination(fake_get_session, auth_headers):
    """GET /goals returns goals newest first; limit and offset work; only current user's goals."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        for i in range(3):
            client.post(
                "/goals",
                json={
                    "original_input": f"input{i}",
                    "refined_goal": f"goal{i}",
                    "key_results": ["A", "B", "C"],
                    "confidence_score": 0.8,
                    "status": "saved",
                },
                headers=auth_headers,
            )
        resp = client.get("/goals", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["goals"]) == 3
        assert data["goals"][0]["refined_goal"] == "goal2"
        assert data["goals"][1]["refined_goal"] == "goal1"
        assert data["goals"][2]["refined_goal"] == "goal0"

        resp2 = client.get("/goals?limit=2&offset=1", headers=auth_headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["total"] == 3
        assert len(data2["goals"]) == 2
        assert data2["goals"][0]["refined_goal"] == "goal1"
        assert data2["goals"][1]["refined_goal"] == "goal0"


def test_get_goals_invalid_params_return_422(fake_get_session, auth_headers):
    """GET /goals with negative offset or limit returns 422."""
    with _with_fake_session(fake_get_session):
        client = TestClient(app)
        resp = client.get("/goals?offset=-1", headers=auth_headers)
        assert resp.status_code == 422
        resp2 = client.get("/goals?limit=-1", headers=auth_headers)
        assert resp2.status_code == 422


def test_goals_scoped_by_user(fake_get_session, in_memory_engine):
    """Two users only see their own goals; GET with token returns only that user's goals."""
    with _with_fake_session(fake_get_session):
        with Session(in_memory_engine) as session:
            u1 = User(username="user1", password_hash=hash_password("p1"))
            u2 = User(username="user2", password_hash=hash_password("p2"))
            session.add(u1)
            session.add(u2)
            session.commit()
            session.refresh(u1)
            session.refresh(u2)
            token1 = create_access_token(u1.id)
            token2 = create_access_token(u2.id)
        client = TestClient(app)
        client.post(
            "/goals",
            json={
                "original_input": "a",
                "refined_goal": "Goal A",
                "key_results": ["x", "y", "z"],
                "confidence_score": 0.9,
                "status": "saved",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )
        client.post(
            "/goals",
            json={
                "original_input": "b",
                "refined_goal": "Goal B",
                "key_results": ["x", "y", "z"],
                "confidence_score": 0.9,
                "status": "saved",
            },
            headers={"Authorization": f"Bearer {token2}"},
        )
        r1 = client.get("/goals", headers={"Authorization": f"Bearer {token1}"})
        r2 = client.get("/goals", headers={"Authorization": f"Bearer {token2}"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["total"] == 1
    assert r2.json()["total"] == 1
    assert r1.json()["goals"][0]["refined_goal"] == "Goal A"
    assert r2.json()["goals"][0]["refined_goal"] == "Goal B"
