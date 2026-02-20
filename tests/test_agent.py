# ABOUTME: Pytest tests for generate_smart_goal and telemetry; mocks ADK Runner/Agent.
# ABOUTME: Verifies GoalModel return and telemetry log_run invocation.

import pytest
from unittest.mock import MagicMock, patch

from goal_coach.agent import generate_smart_goal
from schemas import GoalModel


def _event_with_final_content(json_text: str) -> MagicMock:
    """Build a mock Event that is_final_response and has content with the given text."""
    part = MagicMock()
    part.text = json_text
    content = MagicMock()
    content.parts = [part]
    event = MagicMock()
    event.is_final_response.return_value = True
    event.content = content
    event.usage_metadata = None
    return event


@patch("goal_coach.agent._runner")
def test_generate_smart_goal_returns_valid_goal_model(mock_runner):
    """generate_smart_goal returns a valid GoalModel when the runner yields valid JSON."""
    goal_json = '''{"refined_goal": "Improve public speaking.", "key_results": ["Speak monthly", "Join Toastmasters", "Practice weekly"], "confidence_score": 0.85}'''
    mock_runner.run.return_value = iter(
        [_event_with_final_content(goal_json)]
    )

    result = generate_smart_goal("I want to get better at speaking.")

    assert isinstance(result, GoalModel)
    assert result.refined_goal == "Improve public speaking."
    assert len(result.key_results) == 3
    assert result.confidence_score == 0.85


@patch("goal_coach.agent.log_run")
@patch("goal_coach.agent._runner")
def test_telemetry_callback_invoked_on_success(mock_runner, mock_log_run):
    """Telemetry log_run is called with expected fields when generation succeeds."""
    goal_json = '''{"refined_goal": "Read more.", "key_results": ["A", "B", "C"], "confidence_score": 0.7}'''
    mock_runner.run.return_value = iter(
        [_event_with_final_content(goal_json)]
    )

    generate_smart_goal("Read more books.")

    mock_log_run.assert_called_once()
    call_kw = mock_log_run.call_args.kwargs
    assert "latency_ms" in call_kw
    assert "prompt_tokens" in call_kw
    assert "completion_tokens" in call_kw
    assert call_kw["confidence_score"] == 0.7
    assert call_kw["success"] is True
