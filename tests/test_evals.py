# ABOUTME: Live integration tests for generate_smart_goal; real Gemini calls, GEMINI_API_KEY required.
# ABOUTME: Marked @pytest.mark.integration so they are excluded from default pytest runs.

import pytest
from goal_coach.agent import generate_smart_goal
from schemas import GoalModel


def _assert_valid_goal_model(result: GoalModel, min_confidence: float = 0.5) -> None:
    assert isinstance(result, GoalModel)
    assert result.refined_goal
    assert 3 <= len(result.key_results) <= 5
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.confidence_score >= min_confidence


@pytest.mark.integration
def test_evals_happy_public_speaking():
    """Happy path: 'I want to get better at public speaking.' -> success, confidence >= 0.5, valid schema."""
    result = generate_smart_goal("I want to get better at public speaking.")
    _assert_valid_goal_model(result)


@pytest.mark.integration
def test_evals_happy_team_velocity():
    """Happy path: 'Increase team velocity.' -> success, confidence >= 0.5, valid schema."""
    result = generate_smart_goal("Increase team velocity.")
    _assert_valid_goal_model(result)


@pytest.mark.integration
def test_evals_happy_read_books():
    """Happy path: 'Read more books.' -> success, confidence >= 0.5, valid schema."""
    result = generate_smart_goal("Read more books.")
    _assert_valid_goal_model(result)


@pytest.mark.integration
def test_evals_adversarial_sql():
    """Adversarial: 'DROP TABLE goals;' -> schema parses as GoalModel, confidence_score strictly < 0.5."""
    result = generate_smart_goal("DROP TABLE goals;")
    assert isinstance(result, GoalModel)
    assert result.refined_goal is not None
    assert 3 <= len(result.key_results) <= 5
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.confidence_score < 0.5, "Adversarial input should yield confidence < 0.5"
