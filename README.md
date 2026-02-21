# AI Goal Coach

A small system that turns vague aspirations into structured SMART goals using a single LLM call. Built with FastAPI, Google ADK (Gemini 2.5 Flash), SQLite, and Streamlit.

---

## Design and architecture

### Why this AI model (Gemini 2.5 Flash)

- **Speed and cost:** We need one fast, cheap call per goal. Flash gives low latency and low cost per request (see [core/telemetry.py](core/telemetry.py): $0.075/1M input, $0.30/1M output), which is enough for a prototype and moderate traffic.
- **Single-shot quality:** The task is "refine one goal + 3–5 key results + confidence." We did not need multi-step reasoning or tool use; Flash is sufficient for this scope.
- **Availability:** Google AI Studio and a single API key (`GEMINI_API_KEY`) keep integration simple; no separate auth or model-hosting infra.

**Trade-off:** We gave up the higher reasoning quality of larger models (e.g. Gemini Pro) to keep latency and cost low. If we later need better handling of very ambiguous or adversarial input, we can introduce a second "review" step or a fallback to a larger model for low-confidence cases.

### Why this method for JSON enforcement (ADK `output_schema`)

We need the LLM’s answer to be **strictly** a `GoalModel`: `refined_goal`, `key_results` (3–5 strings), `confidence_score` (0–1). Two options:

1. **Prompt-only:** Ask the model to "return JSON" and parse with Pydantic. Any malformed or extra output forces retries or brittle parsing.
2. **Schema-bound (chosen):** Use Google ADK’s `output_schema=GoalModel` so the request to the model asks for structured output that conforms to the schema. Invalid or non-conforming responses are rejected at the boundary; we return 502 and never pass bad data to the API or DB.

We chose (2) so that the API contract is enforceable by the framework and we avoid silent corruption or repeated retries.

### Trade-offs and what we sacrificed for speed

| Choice | Benefit | Sacrifice |
|--------|---------|-----------|
| **Gemini Flash (not Pro)** | Low latency, low cost | Some reasoning depth; may be weaker on edge/adversarial cases |
| **Single agent, one call** | Simple flow, no chain latency | No in-process "refine again" or validator agent |
| **SQLite** | No DB server, easy local/Docker runs | No high write concurrency; single-file limits |
| **Telemetry to stdout** | No extra backends or SDKs | Dashboards/alerting require a log pipeline |
| **No auth in prototype** | Fast to build and test | Not suitable for multi-tenant production as-is |

We optimized for **getting a working, correct prototype quickly** and for **predictable JSON and cost**. We did not optimize for high concurrency, multi-tenancy, or deep reasoning.

### Scaling to ~10,000 users

At prototype scale the current design is adequate. For ~10k users we would change the following:

1. **Database:** Replace SQLite with a managed RDBMS (e.g. PostgreSQL). Use connection pooling and run migrations (e.g. Alembic). Keep `Goal` and the same API contract; only the engine and deployment change.
2. **API and concurrency:** Run FastAPI behind a production ASGI server (e.g. Uvicorn with workers or behind a reverse proxy). Add rate limiting and optional request queuing so the LLM is not overloaded.
3. **Caching:** Cache results for identical or near-identical `user_input` (e.g. hash + TTL) to reduce duplicate Gemini calls and latency.
4. **Observability:** Ship stdout logs to a log/metrics platform (e.g. GCP Cloud Logging, Datadog). Optionally add OpenTelemetry and export spans/metrics so we can monitor P95 latency, error rate, and cost per user or per day.
5. **Auth and multi-tenancy:** Add authentication (e.g. JWT or OAuth) and scope goals by user/tenant. Use row-level security or tenant IDs so data is isolated.
6. **Model and quality:** If Flash quality is insufficient under load or for edge cases, add a fallback path (e.g. retry with Gemini Pro for low-confidence or after user feedback) or a small "review" step without changing the main flow for the majority of requests.

Update this README when any of these are adopted.

---

## Architecture overview

- **UI:** [Streamlit](ui/app.py) – two tabs: **Refine** (input → POST `/generate`, view result, POST `/goals` to save) and **Saved goals** (GET `/goals`, list saved goals with pagination).
- **API:** [FastAPI](api/main.py) → POST `/generate`, POST `/goals`, GET `/goals` (list, newest first, paginated). Calls [goal_coach](goal_coach/agent.py) (`generate_smart_goal`) and [core/database.py](core/database.py). Returns 400 when confidence &lt; 0.5, 502 on model/schema failure.
- **Agent:** [goal_coach](goal_coach/agent.py) – Google ADK Agent with `output_schema=GoalModel`, model `gemini-2.5-flash`. [core/telemetry.py](core/telemetry.py) logs one JSON line per run to stdout.
- **Storage:** SQLite ([Goal](core/database.py) table); path via `GOALS_DB_PATH` (default `goals.db`).

See [docs/spec.md](docs/spec.md) for the full system specification.

---

## Setup and run

### Prerequisites

- **Without Docker:** Python 3.11+, [uv](https://docs.astral.sh/uv/), and a [Gemini API key](https://aistudio.google.com/apikey).
- **With Docker:** Docker and Docker Compose, and a Gemini API key.

---

### Run without Docker

1. **Clone and install**
   ```bash
   git clone <repo-url>
   cd ai-goal-coach
   uv sync
   ```

2. **Set the Gemini API key**
   Create a `.env` file in the project root (it is in `.gitignore`; do not commit it):
   ```bash
   GEMINI_API_KEY=your_key_here
   ```
   The API and Streamlit app load `.env` via `python-dotenv`.

3. **Start the API** (in one terminal)
   ```bash
   uv run uvicorn api.main:app --reload --port 8000
   ```

4. **Start the UI** (in another terminal)
   ```bash
   uv run streamlit run ui/app.py --server.port 8501
   ```

5. **Use the app**
   - Open http://localhost:8501.
   - **Refine** tab: Enter a goal or aspiration, click "Refine Goal", then "Save Approved Goal" to persist it.
   - **Saved goals** tab: View all saved goals (newest first) with pagination.

6. **Optional: ADK web UI**
   From the project root: `uv run adk web` (discovers the `goal_coach` agent).

---

### Run with Docker

1. **Ensure the API can see your Gemini API key** (see [Passing the Gemini API key securely](#passing-the-gemini-api-key-securely) below).

2. **Build and start**
   ```bash
   docker compose up --build
   ```

3. **Use the app**
   - UI: http://localhost:8501  
   - API: http://localhost:8000  
   - SQLite is stored in the `goal_data` volume for persistence.

#### Passing the Gemini API key securely

The API container needs `GEMINI_API_KEY` to call Gemini. **Never commit the key or bake it into images.** Use one of these:

- **Option A — `.env` file (recommended for local/dev)**  
  Create a `.env` in the project root with:
  ```bash
  GEMINI_API_KEY=your_key_here
  ```
  Docker Compose reads `.env` from the project directory and substitutes `${GEMINI_API_KEY}` into the compose file, so the value is passed into the container at runtime. The file is listed in `.gitignore`, so it is not committed.

- **Option B — Export in the shell**  
  In the same shell where you run Compose:
  ```bash
  export GEMINI_API_KEY=your_key_here
  docker compose up --build
  ```
  The key is not written to a file (assuming your shell history is protected).

- **Option C — Production**  
  Use a secrets manager or Docker secrets; inject the key at runtime and do not store it in repo or in plain env files in production.

---

### Tests

- Unit tests (no API key): `uv run pytest -m "not integration" -v`
- Live evals (requires `GEMINI_API_KEY`): `uv run pytest -m integration -v`

---

## Project layout

- `api/` – FastAPI app (`api/main.py`: `/generate`, `/goals`)
- `ui/` – Streamlit UI (`ui/app.py`)
- `core/` – Shared config, database, schemas, telemetry
- `goal_coach/` – Agent package (`agent.py` with `root_agent` and `generate_smart_goal`)
- `docs/` – Spec, plans, and other documentation
- `tests/` – Unit and integration tests
