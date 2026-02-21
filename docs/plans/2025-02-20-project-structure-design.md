# Project structure design

**Date:** 2025-02-20  
**Goal:** Reorganize the repo so API, UI, and shared code live in clear directories; entry points live with their component (recommended option B).

## Target layout

- **`api/`** – FastAPI app. Entry: `api/main.py` exposing `app`. Run: `uvicorn api.main:app`.
- **`ui/`** – Streamlit app. Entry: `ui/app.py`. Run: `streamlit run ui/app.py` (from repo root).
- **`core/`** – Shared code used by api, ui, and goal_coach: `config.py`, `database.py`, `schemas.py`, `telemetry.py`. Import as `from core.config import ...`, etc.
- **`goal_coach/`** – Unchanged (agent logic). Imports from `core.schemas`, `core.telemetry`.
- **`docs/`** – Project docs. Move `spec.md`, `prompt_plan.md`, `todo.md` into `docs/`. Keep `docs/plans/` for design/implementation plans.
- **Root** – `README.md`, `pyproject.toml`, `docker-compose.yml`, `.env`, `.gitignore`, `Dockerfile.api`, `Dockerfile.ui`, `uv.lock`, `.python-version`. No application Python modules at root.

## Import changes

| From (current) | To (after) |
|----------------|------------|
| `from config import ...` | `from core.config import ...` |
| `from database import ...` | `from core.database import ...` |
| `from schemas import ...` | `from core.schemas import ...` |
| `from telemetry import ...` | `from core.telemetry import ...` |
| `from main import app` (tests) | `from api.main import app` |
| `from goal_coach.agent import ...` | unchanged |
| `from config import ...` (app.py) | `from core.config import ...` (in ui/app.py) |

## Docker

- **Dockerfile.api:** Copy `core/`, `goal_coach/`, `api/`. `WORKDIR /app`. `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
- **Dockerfile.ui:** Copy `ui/`. `CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]`. Streamlit is run from repo root in docker-compose context, so build context must include parent; typically build from repo root and set WORKDIR so that `ui/app.py` is reachable (e.g. copy ui/ to /app/ui/ and run from /app: `streamlit run ui/app.py`).

## Testing

- `pytest` continues to run from repo root. `pyproject.toml` already has `pythonpath = ["."]`; no change needed. Tests update imports to `core.*`, `api.main`.

## Out of scope

- No `src` layout (no `src/ai_goal_coach/`); we keep top-level packages `api`, `ui`, `core`, `goal_coach`.
- No change to `goal_coach` package name or agent behavior.
