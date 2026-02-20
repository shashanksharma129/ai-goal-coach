# Saved Goals List View Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a list view of saved goals (newest first, paginated) and re-add the Save button in the UI, using a two-tab layout (Refine | Saved goals).

**Architecture:** New `GET /goals` endpoint with optional `limit`/`offset` returns `{ "goals": [...], "total": N }`. Streamlit app gets two tabs via `st.tabs()`; Refine tab keeps current flow plus "Save Approved Goal"; Saved goals tab fetches GET /goals and renders list with Previous/Next pagination.

**Tech Stack:** FastAPI, Streamlit, SQLModel, pytest, existing in-memory DB fixture for tests.

**Design reference:** `docs/plans/2026-02-20-saved-goals-list-view-design.md`

---

## Task 1: GET /goals – empty list and shape

**Files:**
- Modify: `tests/test_main.py` (add new tests at end of file)
- Modify: `main.py` (add GET /goals endpoint)

**Step 1: Write the failing test**

Add to `tests/test_main.py`:

```python
def test_get_goals_empty_returns_200_and_empty_list(in_memory_engine):
    """GET /goals with no goals in DB returns 200 and { goals: [], total: 0 }."""
    @contextmanager
    def fake_get_session():
        with Session(in_memory_engine) as s:
            yield s

    with patch("main.get_session", fake_get_session):
        client = TestClient(app)
        resp = client.get("/goals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["goals"] == []
    assert data["total"] == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main.py::test_get_goals_empty_returns_200_and_empty_list -v`  
Expected: FAIL (e.g. 404 or route not found).

**Step 3: Write minimal implementation**

In `main.py`:
- Add to imports: `from fastapi import Query`; `from sqlmodel import select`.
- For total count, use `from sqlalchemy import func` and `total = session.exec(select(func.count()).select_from(Goal)).one()` (or use the scalar result of that one row).
- Add after `post_goals`:

```python
@app.get("/goals")
def get_goals(limit: int = Query(20, ge=0, le=100), offset: int = Query(0, ge=0)):
    """List saved goals, newest first. Returns { goals: [...], total: N }."""
    with get_session() as session:
        total = session.exec(select(func.count()).select_from(Goal)).one()
        stmt = select(Goal).order_by(Goal.created_at.desc()).limit(limit).offset(offset)
        goals = list(session.exec(stmt))
    return {
        "goals": [
            {
                "id": str(g.id),
                "original_input": g.original_input,
                "refined_goal": g.refined_goal,
                "key_results": json.loads(g.key_results),
                "confidence_score": g.confidence_score,
                "status": g.status,
                "created_at": g.created_at.isoformat(),
            }
            for g in goals
        ],
        "total": total,
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main.py::test_get_goals_empty_returns_200_and_empty_list -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat(api): add GET /goals returning empty list and total"
```

---

## Task 2: GET /goals – newest first and pagination

**Files:**
- Modify: `tests/test_main.py`
- Modify: `main.py` (ensure order and pagination)

**Step 1: Write the failing test**

Add to `tests/test_main.py`:

```python
def test_get_goals_returns_newest_first_with_pagination(in_memory_engine):
    """GET /goals returns goals newest first; limit and offset work."""
    @contextmanager
    def fake_get_session():
        with Session(in_memory_engine) as s:
            yield s

    with patch("main.get_session", fake_get_session):
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
            )
        resp = client.get("/goals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["goals"]) == 3
    assert data["goals"][0]["refined_goal"] == "goal2"
    assert data["goals"][1]["refined_goal"] == "goal1"
    assert data["goals"][2]["refined_goal"] == "goal0"

    resp2 = client.get("/goals?limit=2&offset=1")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total"] == 3
    assert len(data2["goals"]) == 2
    assert data2["goals"][0]["refined_goal"] == "goal1"
    assert data2["goals"][1]["refined_goal"] == "goal0"
```

**Step 2: Run test to verify it fails or passes**

Run: `uv run pytest tests/test_main.py::test_get_goals_returns_newest_first_with_pagination -v`  
If implementation from Task 1 already has order_by and limit/offset, this may pass; if not, implement and re-run until PASS.

**Step 3: Ensure implementation**

In `main.py`, `get_goals` must use `select(Goal).order_by(Goal.created_at.desc()).limit(limit).offset(offset)`. Use `Goal.created_at.desc()` (SQLModel/SQLAlchemy). Verify count query and list query are correct.

**Step 4: Run all main tests**

Run: `uv run pytest tests/test_main.py -v`  
Expected: All PASS.

**Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat(api): GET /goals newest first with limit/offset"
```

---

## Task 3: GET /goals – invalid params return 422

**Files:**
- Modify: `tests/test_main.py`

FastAPI returns 422 for invalid Query params (e.g. negative). No change to `main.py` needed.

**Step 1: Write the test**

```python
def test_get_goals_invalid_params_return_422(in_memory_engine):
    """GET /goals with negative offset or limit returns 422."""
    @contextmanager
    def fake_get_session():
        with Session(in_memory_engine) as s:
            yield s

    with patch("main.get_session", fake_get_session):
        client = TestClient(app)
        resp = client.get("/goals?offset=-1")
        assert resp.status_code == 422
        resp2 = client.get("/goals?limit=-1")
        assert resp2.status_code == 422
```

**Step 2: Run test**

Run: `uv run pytest tests/test_main.py::test_get_goals_invalid_params_return_422 -v`  
Expected: PASS (FastAPI Query validation).

**Step 3: Commit**

```bash
git add tests/test_main.py
git commit -m "test(api): GET /goals invalid params return 422"
```

---

## Task 4: UI – Tabs and Refine tab with Save button

**Files:**
- Modify: `app.py`

**Step 1: Add tabs and move current content into Refine tab**

In `app.py`, inside `main()`:
- After `st.title("AI Goal Coach")` and the short description, create two tabs: `tab_refine, tab_saved = st.tabs(["Refine", "Saved goals"])`.
- Wrap the existing block (text area, Refine Goal button, and the block that shows `last_goal`) inside `with tab_refine:`.
- After the confidence metric (inside `with tab_refine:`), add the "Save Approved Goal" button and POST /goals logic (reuse the payload from the design: original_input, refined_goal, key_results, confidence_score, status="saved"). On success: `st.success("Goal saved. Check the Saved goals tab.")`.

**Step 2: Manual check**

Run API and UI locally; open Refine tab, refine a goal, click Save Approved Goal. Expect success message.

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat(ui): add Refine and Saved goals tabs; re-add Save button"
```

---

## Task 5: UI – Saved goals tab (list + empty state)

**Files:**
- Modify: `app.py`

**Step 1: Implement Saved goals tab**

Inside `main()`, after the Refine tab block, add `with tab_saved:`. In it:
- Call `GET {API_URL}/goals?limit=20&offset=0` (use `requests.get`).
- If response is not 200, show `st.error("Could not load saved goals. Try again.")` and return.
- Parse JSON: `data = resp.json()`, `goals = data.get("goals", [])`, `total = data.get("total", 0)`.
- If `len(goals) == 0`, show `st.info("No saved goals yet. Use the Refine tab to create and save one.")` and return.
- Else, for each goal in `goals`, display at least `st.write(goal["refined_goal"])` and `st.caption(goal["created_at"])` (or format created_at). Use expander or simple rows.

**Step 2: Manual check**

Save a goal from Refine tab, switch to Saved goals tab, confirm the goal appears with refined_goal and created_at.

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat(ui): Saved goals tab lists goals with refined_goal and created_at"
```

---

## Task 6: UI – Pagination in Saved goals tab

**Files:**
- Modify: `app.py`

**Step 1: Add pagination state and controls**

- Use `st.session_state` for `saved_goals_page` (default 1). Page size 20.
- In Saved goals tab: compute `offset = (st.session_state.get("saved_goals_page", 1) - 1) * 20`, call `GET /goals?limit=20&offset={offset}`.
- Display "Showing {start}-{end} of {total}" (e.g. start = offset + 1, end = offset + len(goals), total = data["total"]).
- Add two buttons: "Previous" and "Next". Previous: if page > 1, set `st.session_state["saved_goals_page"] -= 1` and `st.rerun()`. Next: if offset + len(goals) < total, set `st.session_state["saved_goals_page"] += 1` and `st.rerun()`.
- If current page is empty and offset > 0 (edge case), refetch with offset=0 and set page to 1.

**Step 2: Manual check**

Create more than 20 goals (or mock), verify Previous/Next and "Showing X–Y of Z".

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat(ui): pagination in Saved goals tab"
```

---

## Task 7: Run full test suite and update README

**Files:**
- Modify: `README.md` (optional: mention Saved goals tab and list view)

**Step 1: Run all tests**

Run: `uv run pytest -v` (exclude integration if no API key: `-m "not integration"`).  
Expected: All pass.

**Step 2: Update README**

In "Architecture overview" or "Setup and run", add one line that the UI has two tabs (Refine and Saved goals) and that saved goals can be viewed in the Saved goals tab. Optional.

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: mention Saved goals tab in README"
```

---

## Execution handoff

Plan complete and saved to `docs/plans/2026-02-20-saved-goals-list-view.md`.

**Two execution options:**

1. **Subagent-driven (this session)** – I run each task (or dispatch a subagent per task), you review between tasks; fast iteration.
2. **Parallel session (separate)** – You open a new session (e.g. in the same repo or worktree), use the executing-plans skill there, and run through the plan with checkpoints.

Which approach do you want?
