# ABOUTME: Tests for UI helpers (e.g. saved-goals label formatting).
# ABOUTME: Keeps UI logic testable without running Streamlit.

import pytest

from ui.app import _saved_goal_expander_label


def test_saved_goal_expander_label_truncates_long_goal():
    goal = {
        "refined_goal": "A" * 100,
        "key_results": ["a", "b", "c"],
        "created_at": "2026-02-22T12:00:00+00:00",
        "confidence_score": 0.9,
    }
    label = _saved_goal_expander_label(goal, max_chars=20)
    assert "…" in label
    assert "Feb 22, 2026" in label
    assert "0.90" in label


def test_saved_goal_expander_label_short_goal_no_truncation():
    goal = {
        "refined_goal": "Read 12 books.",
        "key_results": [],
        "created_at": "2026-02-22T00:00:00+00:00",
        "confidence_score": 0.95,
    }
    label = _saved_goal_expander_label(goal, max_chars=80)
    assert "Read 12 books" in label
    assert "Feb 22, 2026" in label
    assert "0.95" in label
