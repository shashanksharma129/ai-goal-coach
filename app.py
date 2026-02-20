# ABOUTME: Streamlit UI for AI Goal Coach; calls FastAPI backend for generate and save.
# ABOUTME: API URL configurable via API_URL env (default http://localhost:8000).

import os
import streamlit as st
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_URL = os.environ.get("API_URL", "http://localhost:8000")


def _safe_json(response: requests.Response):
    """Parse response body as JSON; return dict or empty dict on failure."""
    try:
        return response.json()
    except Exception:
        return {}


def main():
    st.title("AI Goal Coach")
    st.write("Enter a vague goal or aspiration below and refine it into a SMART goal.")

    tab_refine, tab_saved = st.tabs(["Refine", "Saved goals"])

    with tab_refine:
        user_input = st.text_area(
            "Your goal or aspiration",
            placeholder="e.g. I want to get better at public speaking.",
            height=100,
        )

        if st.button("Refine Goal"):
            if not (user_input and user_input.strip()):
                st.error("Please enter a goal or aspiration.")
            else:
                with st.spinner("Refining your goal..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/generate",
                            json={"user_input": user_input.strip()},
                            timeout=60,
                        )
                        if r.status_code == 200:
                            data = _safe_json(r)
                            if not data or "refined_goal" not in data:
                                st.error("Invalid response from server. Please try again.")
                                return
                            st.session_state["last_goal"] = data
                            st.session_state["last_original_input"] = user_input.strip()
                        elif r.status_code == 400:
                            body = _safe_json(r)
                            msg = body.get("message", r.text or "Input too vague or invalid.")
                            st.error(msg)
                            return
                        elif r.status_code == 502:
                            body = _safe_json(r)
                            msg = body.get("message", r.text or "AI model failed to generate a valid response.")
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
            st.subheader("Refined goal")
            st.write(goal["refined_goal"])
            st.subheader("Key results")
            for kr in goal["key_results"]:
                st.markdown(f"- {kr}")
            st.metric("Confidence score", f"{goal['confidence_score']:.2f}")

            if st.button("Save Approved Goal"):
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
                        timeout=10,
                    )
                    if r.status_code == 200:
                        st.success("Goal saved. Check the Saved goals tab.")
                    else:
                        body = _safe_json(r)
                        msg = body.get("message", r.text or "Save failed.")
                        st.error(f"Save failed: {r.status_code} – {msg}")
                except requests.RequestException as e:
                    st.error(f"Could not reach the API: {e}")

    with tab_saved:
        try:
            r = requests.get(f"{API_URL}/goals", params={"limit": 20, "offset": 0}, timeout=10)
        except requests.RequestException:
            st.error("Could not load saved goals. Try again.")
        else:
            if r.status_code != 200:
                st.error("Could not load saved goals. Try again.")
            else:
                data = _safe_json(r)
                goals = data.get("goals", [])
                total = data.get("total", 0)
                if not goals:
                    st.info("No saved goals yet. Use the Refine tab to create and save one.")
                else:
                    for g in goals:
                        st.write(g["refined_goal"])
                        st.caption(g.get("created_at", ""))


if __name__ == "__main__":
    main()
