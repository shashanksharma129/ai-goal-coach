# ABOUTME: Streamlit UI: Login/signup, then Refine tab (generate + save) and Saved goals tab (GET /goals).
# ABOUTME: API URL configurable via API_URL env; JWT stored in session_state, sent as Bearer on requests.

import os
from datetime import datetime

import requests
import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from core.config import DEFAULT_GOALS_PAGE_SIZE

API_URL = os.environ.get("API_URL", "http://localhost:8000")
SESSION_ACCESS_TOKEN = "access_token"
SAVED_GOAL_SUMMARY_MAX_CHARS = 80


_SAVED_GOAL_DATE_PREFIX = "Created on "


def _saved_goal_expander_label(
    goal: dict, max_chars: int = SAVED_GOAL_SUMMARY_MAX_CHARS
) -> str:
    """Build expander label: truncated refined_goal and creation date (clearly labeled)."""
    text = (goal.get("refined_goal") or "").strip()
    summary = (text[:max_chars] + "…") if len(text) > max_chars else text
    date_str = ""
    if goal.get("created_at"):
        try:
            dt = datetime.fromisoformat(goal["created_at"].replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            raw = goal.get("created_at", "")
            date_str = raw[:10] if len(raw) >= 10 else ""
    if date_str:
        return f"{summary}  ·  {_SAVED_GOAL_DATE_PREFIX}{date_str}"
    return summary


def _safe_json(response: requests.Response):
    """Parse response body as JSON; return dict or empty dict on failure."""
    try:
        return response.json()
    except Exception:
        return {}


def _auth_headers():
    """Return headers with Bearer token for authenticated API calls, or empty dict if not logged in."""
    token = st.session_state.get(SESSION_ACCESS_TOKEN)
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _clear_auth_and_rerun():
    """Remove token from session and rerun to show login screen."""
    if SESSION_ACCESS_TOKEN in st.session_state:
        del st.session_state[SESSION_ACCESS_TOKEN]
    st.rerun()


def _render_login_signup():
    """Show Login and Sign up tabs; on success set access_token and rerun."""
    st.title("AI Goal Coach")
    st.write("Sign in or create an account to continue.")

    tab_login, tab_signup = st.tabs(["Login", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input(
                "Password", type="password", key="login_password"
            )
            if st.form_submit_button("Sign in"):
                if not (login_username and login_username.strip() and login_password):
                    st.error("Enter username and password.")
                else:
                    try:
                        r = requests.post(
                            f"{API_URL}/auth/login",
                            json={
                                "username": login_username.strip(),
                                "password": login_password,
                            },
                            timeout=10,
                        )
                        if r.status_code == 200:
                            data = _safe_json(r)
                            token = data.get("access_token")
                            if token:
                                st.session_state[SESSION_ACCESS_TOKEN] = token
                                st.rerun()
                            else:
                                st.error("Invalid response from server.")
                        else:
                            body = _safe_json(r)
                            st.error(
                                body.get("message", "Invalid username or password.")
                            )
                    except requests.RequestException as e:
                        st.error(f"Could not reach the API: {e}")

    with tab_signup:
        with st.form("signup_form"):
            signup_username = st.text_input("Username", key="signup_username")
            signup_password = st.text_input(
                "Password", type="password", key="signup_password"
            )
            if st.form_submit_button("Create account"):
                if not (
                    signup_username and signup_username.strip() and signup_password
                ):
                    st.error("Enter username and password.")
                else:
                    try:
                        r = requests.post(
                            f"{API_URL}/auth/signup",
                            json={
                                "username": signup_username.strip(),
                                "password": signup_password,
                            },
                            timeout=10,
                        )
                        if r.status_code == 201:
                            data = _safe_json(r)
                            token = data.get("access_token")
                            if token:
                                st.session_state[SESSION_ACCESS_TOKEN] = token
                                st.rerun()
                            else:
                                st.error(
                                    "Invalid response from server (no token). Please sign in on the Login tab."
                                )
                        elif r.status_code == 409:
                            st.error("Username already taken.")
                        elif r.status_code == 400:
                            body = _safe_json(r)
                            st.error(body.get("message", "Invalid input."))
                        else:
                            body = _safe_json(r)
                            st.error(body.get("message", "Sign up failed."))
                    except requests.RequestException as e:
                        st.error(f"Could not reach the API: {e}")


def main():
    if not st.session_state.get(SESSION_ACCESS_TOKEN):
        _render_login_signup()
        return

    if st.sidebar.button("Logout"):
        _clear_auth_and_rerun()
        return

    st.title("AI Goal Coach")
    st.write("Enter a vague goal or aspiration below and refine it into a SMART goal.")

    tab_refine, tab_saved = st.tabs(["Refine", "Saved goals"])

    with tab_refine:
        user_input = st.text_area(
            "Your goal or aspiration",
            placeholder="e.g. I want to get better at public speaking.",
            height=100,
        )

        if st.button("Refine Goal", key="refine_goal_btn"):
            if not (user_input and user_input.strip()):
                st.error("Please enter a goal or aspiration.")
            else:
                with st.spinner("Refining your goal..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/generate",
                            json={"user_input": user_input.strip()},
                            headers=_auth_headers(),
                            timeout=60,
                        )
                        if r.status_code == 200:
                            data = _safe_json(r)
                            if not data or "refined_goal" not in data:
                                st.error(
                                    "Invalid response from server. Please try again."
                                )
                                return
                            st.session_state["last_goal"] = data
                            st.session_state["last_original_input"] = user_input.strip()
                            if data.get("session_id"):
                                st.session_state["goal_session_id"] = data["session_id"]
                        elif r.status_code == 401:
                            _clear_auth_and_rerun()
                            return
                        elif r.status_code == 400:
                            body = _safe_json(r)
                            msg = body.get(
                                "message", r.text or "Input too vague or invalid."
                            )
                            st.error(msg)
                            return
                        elif r.status_code == 502:
                            body = _safe_json(r)
                            msg = body.get(
                                "message",
                                r.text
                                or "AI model failed to generate a valid response.",
                            )
                            st.error(msg)
                            return
                        else:
                            st.error(f"Unexpected error: {r.status_code}")
                            return
                    except requests.RequestException as e:
                        st.error(f"Could not reach the API: {e}")
                        return

        if "last_goal" in st.session_state:
            goal = st.session_state["last_goal"]
            with st.container(border=True):
                st.subheader("Refined goal")
                st.write(goal["refined_goal"])
                st.subheader("Key results")
                for kr in goal["key_results"]:
                    st.markdown(f"- {kr}")
                st.metric("Confidence score", f"{goal['confidence_score']:.2f}")

            st.divider()
            with st.container(border=True):
                st.subheader("Refine further")
                st.caption(
                    "Ask for changes—tone, deadline, constraints—and get an updated goal."
                )
                feedback_key = "refine_further_feedback"
                feedback = st.text_area(
                    "Your feedback",
                    placeholder="e.g. Make the deadline 6 months, or add a key result about finishing 2 books.",
                    height=80,
                    key=feedback_key,
                )
                refine_further_clicked = st.button(
                    "Refine further", key="refine_further_btn"
                )
            if refine_further_clicked:
                sid = st.session_state.get("goal_session_id")
                if not (feedback and feedback.strip()):
                    st.error("Please enter feedback.")
                elif not sid:
                    st.error("Session lost. Refine a new goal above to start over.")
                else:
                    with st.spinner("Applying your feedback..."):
                        try:
                            r = requests.post(
                                f"{API_URL}/generate",
                                json={
                                    "user_input": feedback.strip(),
                                    "session_id": sid,
                                },
                                headers=_auth_headers(),
                                timeout=60,
                            )
                            if r.status_code == 200:
                                data = _safe_json(r)
                                if data and "refined_goal" in data:
                                    st.session_state["last_goal"] = data
                                    if data.get("session_id"):
                                        st.session_state["goal_session_id"] = data[
                                            "session_id"
                                        ]
                                    st.session_state[feedback_key] = ""
                                    st.rerun()
                                else:
                                    st.error(
                                        "Invalid response from server. Please try again."
                                    )
                            elif r.status_code == 401:
                                _clear_auth_and_rerun()
                                return
                            elif r.status_code == 400:
                                body = _safe_json(r)
                                st.error(
                                    body.get(
                                        "message",
                                        r.text or "Input too vague or invalid.",
                                    )
                                )
                            elif r.status_code == 502:
                                body = _safe_json(r)
                                st.error(
                                    body.get(
                                        "message",
                                        r.text
                                        or "AI model failed to generate a valid response.",
                                    )
                                )
                            else:
                                st.error(f"Unexpected error: {r.status_code}")
                        except requests.RequestException as e:
                            st.error(f"Could not reach the API: {e}")

            st.caption("Happy with this version? Save it to your list.")
            if st.button("Save Approved Goal", key="save_goal_btn"):
                original = st.session_state.get("last_original_input", "")
                try:
                    r = requests.post(
                        f"{API_URL}/goals",
                        json={
                            "original_input": original,
                            "refined_goal": goal["refined_goal"],
                            "key_results": goal["key_results"],
                            "confidence_score": goal["confidence_score"],
                            "status": "saved",
                        },
                        headers=_auth_headers(),
                        timeout=10,
                    )
                    if r.status_code == 200:
                        st.success("Goal saved. Check the Saved goals tab.")
                        for key in (
                            "last_goal",
                            "last_original_input",
                            "goal_session_id",
                        ):
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    elif r.status_code == 401:
                        _clear_auth_and_rerun()
                        return
                    else:
                        body = _safe_json(r)
                        msg = body.get("message", r.text or "Save failed.")
                        st.error(f"Save failed: {r.status_code} – {msg}")
                except requests.RequestException as e:
                    st.error(f"Could not reach the API: {e}")

    with tab_saved:
        page_size = DEFAULT_GOALS_PAGE_SIZE
        if "saved_goals_page" not in st.session_state:
            st.session_state["saved_goals_page"] = 1
        page = st.session_state["saved_goals_page"]
        offset = (page - 1) * page_size

        try:
            r = requests.get(
                f"{API_URL}/goals",
                params={"limit": page_size, "offset": offset},
                headers=_auth_headers(),
                timeout=10,
            )
        except requests.RequestException as e:
            st.error(f"Could not load saved goals. Try again. Error: {e}")
            return
        if r.status_code == 401:
            _clear_auth_and_rerun()
            return
        if r.status_code != 200:
            body = _safe_json(r)
            msg = body.get("message", "Could not load saved goals. Try again.")
            st.error(msg)
            return
        data = _safe_json(r)
        goals = data.get("goals", [])
        total = data.get("total", 0)
        if not goals and offset > 0:
            st.session_state["saved_goals_page"] = 1
            st.rerun()
        if not goals:
            st.info("No saved goals yet. Use the Refine tab to create and save one.")
            return
        start = offset + 1
        end = offset + len(goals)
        st.caption(f"Showing {start}–{end} of {total}")
        for g in goals:
            label = _saved_goal_expander_label(g)
            with st.expander(label, expanded=False):
                st.caption("**Refined goal**")
                st.write(g["refined_goal"])
                if g.get("key_results"):
                    st.caption("**Key results**")
                    for kr in g["key_results"]:
                        st.markdown(f"- {kr}")
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("Previous", disabled=(page <= 1), key="prev_goals"):
                st.session_state["saved_goals_page"] = page - 1
                st.rerun()
        with col_next:
            if st.button(
                "Next", disabled=(offset + len(goals) >= total), key="next_goals"
            ):
                st.session_state["saved_goals_page"] = page + 1
                st.rerun()


if __name__ == "__main__":
    main()
