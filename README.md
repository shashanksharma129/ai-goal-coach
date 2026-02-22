# AI Goal Coach

Turns vague aspirations into structured SMART goals. Users sign up or log in, refine a goal (and can iteratively "Refine further" in the same thread), then save. Stack: FastAPI, Google ADK (Gemini 2.5 Flash) with session state, SQLite, Streamlit.

This README is the **architecture decision record**: it explains design choices first, then [setup](#setup-and-run).

---

## 1. Why this AI model (Gemini 2.5 Flash)

- **Speed and cost:** One fast, cheap call per goal. Flash gives low latency and low cost ([core/telemetry.py](core/telemetry.py): $0.075/1M input, $0.30/1M output).
- **Fit for task:** We need “refine goal + 3–5 key results + confidence.” No multi-step reasoning or tools; Flash is enough.
- **Simplicity:** One API key (`GEMINI_API_KEY`), no extra auth or hosting.

**Trade-off:** We gave up the higher reasoning quality of larger models (e.g. Gemini Pro). For ambiguous or adversarial input we could add a review step or fallback to a larger model later.

---

## 2. Why this method for JSON enforcement (ADK `output_schema`)

We need strict `GoalModel` output: `refined_goal`, `key_results` (3–5 strings), `confidence_score` (0–1).

- **Prompt-only:** Ask for JSON and parse with Pydantic → malformed output forces retries or brittle parsing.
- **Schema-bound (chosen):** ADK `output_schema=GoalModel` → model returns structured output; invalid responses are rejected at the boundary, we return 502 and never pass bad data through.

We chose schema-bound so the API contract is enforceable and we avoid silent corruption.

---

## 3. Trade-offs: what we sacrificed for speed

| Choice | Benefit | Sacrifice |
|--------|---------|-----------|
| Gemini Flash (not Pro) | Low latency, low cost | Weaker on edge/adversarial cases |
| Single agent, iterative refinement | Simple flow; "Refine further" reuses same session | No separate validator agent |
| SQLite | No DB server, easy local/Docker | No high write concurrency |
| Telemetry to stdout | No extra backends | Dashboards need a log pipeline |
| JWT auth, goals per user | Multi-tenant isolation | Token/session handling in UI |

We optimized for a correct, fast prototype and predictable JSON and cost; we did not optimize for high concurrency or deep reasoning.

---

## 4. Scaling to ~10,000 users

Current design is adequate at prototype scale. For ~10k users we would:

1. **Database:** Replace SQLite with a managed RDBMS (e.g. PostgreSQL), connection pooling, migrations (e.g. Alembic). Same `Goal` contract.
2. **API and concurrency:** Production ASGI server (e.g. Uvicorn with workers), rate limiting, optional request queuing for the LLM.
3. **Caching:** Cache by `user_input` (hash + TTL) to cut duplicate Gemini calls.
4. **Observability:** Ship logs to a platform (e.g. GCP, Datadog); optional OpenTelemetry for latency, error rate, cost.
5. **Auth:** Already implemented ([Authentication and multi-tenancy](#authentication-and-multi-tenancy)). Goals scoped by `user_id` in app code. At 10k we could add row-level security (RLS) in the DB as defense-in-depth.
6. **Model quality:** If Flash is insufficient, add a fallback (e.g. Gemini Pro for low-confidence) or a small review step.

Update this README when any of these are adopted.

---

## Authentication and multi-tenancy

- **Sign up:** POST `/auth/signup` with `{"username": "your_user", "password": "your_password"}` → 201. Response includes `access_token`; passwords hashed ([core/auth.py](core/auth.py)), never stored plain.
- **Login:** POST `/auth/login` with `{"username": "your_user", "password": "your_password"}` → `{"access_token": "...", "token_type": "bearer", "expires_in": N}`. UI sends `Authorization: Bearer <token>` on `/generate` and `/goals`.
- **Isolation:** Goals stored with `user_id`; GET/POST `/goals` only touch the authenticated user's data. The `/generate` endpoint passes the authenticated user's id to the agent so ADK session history is isolated per user (no cross-user session access).

UI: Login / Sign up when unauthenticated; after login, Refine and Saved goals tabs; Logout in sidebar.

---

## Architecture overview

- **UI** ([ui/app.py](ui/app.py)): Login/Sign up → Refine (POST `/generate`, then optionally "Refine further" with feedback in the same thread, then POST `/goals` to save) and Saved goals (GET `/goals`, paginated).
- **API** ([api/main.py](api/main.py)): `/auth/signup`, `/auth/login`; `/generate` (optional `session_id` for iterative refinement; response includes `session_id`, `refined_goal`, `key_results`, `confidence_score`); `/goals` (JWT required, goals scoped by user). 400 low confidence/bad input, 401 unauthenticated, 502 model/schema failure.
- **Agent** ([goal_coach/agent.py](goal_coach/agent.py)): ADK agent with session state keyed by authenticated `user_id` for per-user isolation. First message in a thread produces an initial SMART goal (Role A); follow-up messages in the same session apply feedback and return an updated goal (Role B). Empty or missing `session_id` starts a new thread. `output_schema=GoalModel`, `gemini-2.5-flash`. [core/telemetry.py](core/telemetry.py) logs one JSON line per run.
- **Storage** ([core/database.py](core/database.py)): SQLite, `users` + `goals` (with `user_id`); `GOALS_DB_PATH` (default `goals.db`).

Code: `ABOUTME` at top of modules, docstrings on public APIs, unit and integration tests. See [docs/spec.md](docs/spec.md) for full spec.

---

## Setup and run

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), [Gemini API key](https://aistudio.google.com/apikey). With Docker: Docker Compose + API key.

### Without Docker

1. Clone, install, set API key:
   ```bash
   git clone <repo-url>
   cd ai-goal-coach
   uv sync
   ```
   Add a `.env` in the project root (in `.gitignore`): `GEMINI_API_KEY=your_key_here` and `SECRET_KEY=your-secret` (required for JWT; use a long random string). Optional: `CORS_ORIGINS=http://localhost:8501` (default) or comma-separated origins for production.

2. Start API: `uv run uvicorn api.main:app --reload --port 8000`

3. Start UI (other terminal): `uv run streamlit run ui/app.py --server.port 8501`

4. Open http://localhost:8501 → Sign up or Login → Refine tab (refine goal, optionally "Refine further" with feedback in the same thread, then save) or Saved goals (list, paginated). Logout in sidebar.

Optional: `uv run adk web` for ADK web UI.

### With Docker

1. Set `GEMINI_API_KEY` (e.g. in `.env` in project root; Compose injects it; do not commit).
2. `docker compose up --build`
3. UI: http://localhost:8501, API: http://localhost:8000. SQLite in `goal_data` volume.

Never commit the key; for production use a secrets manager or Docker secrets.

### Tests

- Unit (no API key): `uv run pytest -m "not integration" -v`
- Integration (needs `GEMINI_API_KEY`): `uv run pytest -m integration -v`

### Linting and formatting (Ruff)

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. Install dev deps, then run:

- **Lint:** `uv run ruff check .`
- **Format:** `uv run ruff format .`

Ruff is in the `dev` optional dependency group (`uv sync --extra dev`).

---

## Project layout

| Dir | Purpose |
|-----|---------|
| `api/` | FastAPI: `/auth/signup`, `/auth/login`, `/generate`, `/goals` |
| `ui/` | Streamlit app |
| `core/` | Config, database, schemas, telemetry, auth |
| `goal_coach/` | ADK agent (`generate_smart_goal`) |
| `docs/` | Spec and plans |
| `tests/` | Unit and integration tests |
