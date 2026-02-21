# Project Structure Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move API and UI into `api/` and `ui/`, shared code into `core/`, and docs into `docs/`, with entry points in subdirs and all imports/Docker/README updated.

**Architecture:** See [2025-02-20-project-structure-design.md](2025-02-20-project-structure-design.md). We add `core/`, `api/`, `ui/` packages; move files; update every import to `core.*` and `api.main`; update Dockerfiles and README.

**Tech Stack:** Python 3.11+, FastAPI, Streamlit, pytest, Docker. No new dependencies.

---

## Task 1: Create `core/` package and move shared modules

**Files:**
- Create: `core/__init__.py` (empty or re-export if desired)
- Create: `core/config.py` (move from `config.py`, keep content; update ABOUTME to mention core package)
- Create: `core/database.py` (move from `database.py`)
- Create: `core/schemas.py` (move from `schemas.py`)
- Create: `core/telemetry.py` (move from `telemetry.py`)

**Step 1:** Create `core/` and the four module files with the same content as the current root files. Do not delete the root files yet.

**Step 2:** Update `goal_coach/agent.py`: change `from schemas import GoalModel` to `from core.schemas import GoalModel` and `from telemetry import log_run` to `from core.telemetry import log_run`.

**Step 3:** Update `main.py`: change `from config import ...` to `from core.config import ...`, `from database import ...` to `from core.database import ...`, `from schemas import ...` to `from core.schemas import ...`.

**Step 4:** Update `app.py`: change `from config import DEFAULT_GOALS_PAGE_SIZE` to `from core.config import DEFAULT_GOALS_PAGE_SIZE`.

**Step 5:** Update tests: in `tests/test_agent.py` use `from core.schemas import GoalModel`; in `tests/test_main.py` use `from core.database import Goal`, `from core.schemas import GoalModel`; in `tests/test_database.py` use `from core.database import Goal`; in `tests/test_evals.py` use `from core.schemas import GoalModel`. In `tests/test_agent.py` change the telemetry mock to patch `core.telemetry.log_run` (e.g. `@patch("goal_coach.agent.log_run")` stays if agent imports `log_run` from core.telemetry — so patch `core.telemetry.log_run` or the symbol where it’s used: `goal_coach.agent.log_run`; keep patching at use site so no change if already `goal_coach.agent.log_run`).

**Step 6:** Run tests: `uv run pytest -m "not integration" -v`. Fix any import errors until all pass.

**Step 7:** Delete root `config.py`, `database.py`, `schemas.py`, `telemetry.py`.

**Step 8:** Commit: `git add core/ goal_coach/ main.py app.py tests/ && git add -u config.py database.py schemas.py telemetry.py && git commit -m "refactor: add core package with config, database, schemas, telemetry"`

---

## Task 2: Create `api/` package and move FastAPI app

**Files:**
- Create: `api/__init__.py` (empty)
- Create: `api/main.py` (move content from `main.py`; ensure imports use `core.*` and `goal_coach.agent`)
- Modify: remove root `main.py` after move

**Step 1:** Create `api/__init__.py` (empty). Create `api/main.py` with the full content of current `main.py` (already using core.* after Task 1). Ensure first line comment (ABOUTME) is preserved.

**Step 2:** Update `tests/test_main.py`: change `from main import app` to `from api.main import app`.

**Step 3:** Run tests: `uv run pytest -m "not integration" -v`. Fix until pass.

**Step 4:** Delete root `main.py`.

**Step 5:** Commit: `git add api/ tests/ && git rm main.py && git commit -m "refactor: move FastAPI app into api/main.py"`

---

## Task 3: Create `ui/` package and move Streamlit app

**Files:**
- Create: `ui/__init__.py` (empty)
- Create: `ui/app.py` (move content from `app.py`; imports from `core.config`)
- Remove: root `app.py` after move

**Step 1:** Create `ui/__init__.py` (empty). Create `ui/app.py` with the full content of current `app.py` (already using `core.config` after Task 1).

**Step 2:** Run tests: `uv run pytest -m "not integration" -v` (no UI tests; API tests must still pass).

**Step 3:** Delete root `app.py`.

**Step 4:** Commit: `git add ui/ && git rm app.py && git commit -m "refactor: move Streamlit app into ui/app.py"`

---

## Task 4: Update Dockerfiles

**Files:**
- Modify: `Dockerfile.api`
- Modify: `Dockerfile.ui`

**Step 1:** Update `Dockerfile.api`: Copy `core/`, `goal_coach/`, `api/`. CMD: `["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`. Ensure dependencies (e.g. from pyproject) are installed; current Dockerfile uses `pip install ...`; add no extra packages. Copy lines:
  ```
  COPY core/ ./core/
  COPY goal_coach/ ./goal_coach/
  COPY api/ ./api/
  ```
  Remove old COPY of `main.py database.py schemas.py telemetry.py`. CMD as above.

**Step 2:** Update `Dockerfile.ui`: Copy `ui/` into image (e.g. `COPY ui/ ./ui/`). CMD: `["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]`. Ensure WORKDIR is `/app` so that `ui/app.py` is at `/app/ui/app.py`.

**Step 3:** (Optional) Build and run: `docker compose up --build` and smoke-test API at :8000 and UI at :8501. Document in plan that executor may do this.

**Step 4:** Commit: `git add Dockerfile.api Dockerfile.ui && git commit -m "chore(docker): point Dockerfiles at api/ and ui/"`

---

## Task 5: Move docs to `docs/` and update README

**Files:**
- Create/move: `docs/spec.md` (move from `spec.md`), `docs/prompt_plan.md` (from `prompt_plan.md`), `docs/todo.md` (from `todo.md`)
- Modify: `README.md` – update links and run commands

**Step 1:** Move `spec.md`, `prompt_plan.md`, `todo.md` to `docs/` (e.g. `mv spec.md docs/` etc.). Do not move `docs/plans/` content.

**Step 2:** In `README.md`: replace `main:app` with `api.main:app` and `app.py` with `ui/app.py` in run commands. Replace links like `[main.py](main.py)` with `[api/main.py](api/main.py)`, `[app.py](app.py)` with `[ui/app.py](ui/app.py)`, `[database.py](database.py)` with `[core/database.py](core/database.py)`, `[telemetry.py](telemetry.py)` with `[core/telemetry.py](core/telemetry.py)`, `[spec.md](spec.md)` with `[docs/spec.md](docs/spec.md)`. Update the "Project layout" section to list `api/`, `ui/`, `core/`, `goal_coach/`, `docs/`, `tests/`.

**Step 3:** Run tests again: `uv run pytest -m "not integration" -v`.

**Step 4:** Commit: `git add docs/ README.md && git rm spec.md prompt_plan.md todo.md 2>/dev/null; git add -u && git commit -m "docs: move spec, prompt_plan, todo to docs/; update README for new layout"`

---

## Task 6: Final verification

**Step 1:** From repo root run:
- `uv run uvicorn api.main:app --port 8000` (start in background or second terminal), then `curl -s http://localhost:8000/docs` should return HTML.
- `uv run streamlit run ui/app.py --server.port 8501` (or verify command runs and exits cleanly with --help).

**Step 2:** Full test run: `uv run pytest -m "not integration" -v`. Output must be pristine; all tests pass.

**Step 3:** If anything fails, fix and amend or add a fix commit. Then mark plan complete.

---

## Summary of new layout

```
api/
  __init__.py
  main.py          # FastAPI app
ui/
  __init__.py
  app.py           # Streamlit app
core/
  __init__.py
  config.py
  database.py
  schemas.py
  telemetry.py
goal_coach/
  __init__.py
  agent.py
docs/
  spec.md
  prompt_plan.md
  todo.md
  plans/
    ...
tests/
  ...
README.md, pyproject.toml, docker-compose.yml, Dockerfile.api, Dockerfile.ui, .env, .gitignore
```
