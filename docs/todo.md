# AI Goal Coach - Project Checklist

## Phase 0: Project Setup & Prerequisites
- Create a new Git repository for the project.
- Get a Google Gemini API Key from Google AI Studio.
- Set up a Python virtual environment (`python -m venv venv` and `source venv/bin/activate`).
- Create a `.env` file and add `GEMINI_API_KEY=your_key_here` (ensure `.env` is in `.gitignore`).

## Phase 1: Data Models & Database Setup
- **Dependencies:** Create `requirements.txt` and install: `fastapi`, `uvicorn`, `sqlmodel`, `pydantic`, `pytest`, `pytest-asyncio`, `google-genai`, `google-agent-development-kit`.
- **Schemas (`schemas.py`):**
  - Define `GoalModel` inheriting from `pydantic.BaseModel`.
  - Add `refined_goal` (str) with description.
  - Add `key_results` (list) with `min_length=3`, `max_length=5`.
  - Add `confidence_score` (float) with bounds `ge=0.0`, `le=1.0`.
- **Database (`database.py`):**
  - Define `Goal` table using `SQLModel` (table=True).
  - Include fields: `id` (UUID, primary_key), `original_input` (str), `refined_goal` (str), `key_results` (str/JSON), `confidence_score` (float), `status` (str, default='draft'), `created_at` (datetime).
  - Implement `get_session()` to yield an SQLite session.
  - Implement database initialization logic (`SQLModel.metadata.create_all`).
- **Testing (`test_database.py`):**
  - Write pytest fixture for an in-memory SQLite database (`sqlite:///:memory:`).
  - Write test to create, save, and read a `Goal` record.
  - Run `pytest test_database.py` and ensure it passes.

## Phase 2: Google ADK Agent & Telemetry
- **Telemetry (`telemetry.py`):**
  - Create a custom ADK Runner callback/listener class.
  - Implement extraction of execution metrics (latency, token usage).
  - Implement cost calculation function for `gemini-2.5-flash` ($0.075/1M input, $0.30/1M output).
  - Format and print structured JSON log to `stdout` upon run completion.
- **Agent (`agent.py`):**
  - Import `LlmAgent` and `Runner` from `google.adk`.
  - Instantiate `LlmAgent` configured with model `gemini-2.5-flash`.
  - Attach `output_schema=GoalModel` to the agent.
  - Create `generate_smart_goal(user_input: str) -> GoalModel` function.
  - Inside the function, invoke the `Runner`, passing the agent and the telemetry callback.
- **Testing (`test_agent.py`):**
  - Mock the ADK `Runner` and `LlmAgent` using `unittest.mock`.
  - Write test to verify `generate_smart_goal` returns a valid mock `GoalModel`.
  - Write test to verify the telemetry callback is triggered.
  - Run `pytest test_agent.py` and ensure it passes.

## Phase 3: FastAPI Backend
- **API Setup (`main.py`):**
  - Initialize FastAPI app instance.
  - Add CORS middleware if needed for local frontend testing.
- **Endpoint: `POST /generate`:**
  - Accept JSON payload `{"user_input": "..."}`.
  - Call `generate_smart_goal(user_input)`.
  - Implement Guardrail 1: If `confidence_score < 0.5`, raise `HTTPException(400)`.
  - Implement Guardrail 2: Wrap generation in `try/except`; on ADK/schema failure, raise `HTTPException(502)`.
  - Return the generated `GoalModel` JSON.
- **Endpoint: `POST /goals`:**
  - Accept complete goal data payload.
  - Save to SQLite using `get_session()` and `Goal` SQLModel.
  - Return the saved database record.
- **Testing (`test_main.py`):**
  - Set up `fastapi.testclient.TestClient`.
  - Write test for successful `POST /generate` (mocking agent).
  - Write test for 400 Bad Request logic (mocking agent to return low confidence).
  - Write test for 502 Bad Gateway logic (mocking agent to throw exception).
  - Write test for `POST /goals` to verify DB persistence.
  - Run `pytest test_main.py` and verify 100% pass rate.

## Phase 4: Streamlit Frontend
- **Frontend Setup:** Add `streamlit` and `requests` to `requirements.txt`.
- **UI Implementation (`app.py`):**
  - Render Page Title ("AI Goal Coach").
  - Render input text area for the vague goal.
  - Render "Refine Goal" button.
  - On click, send POST request to `http://localhost:8000/generate`.
  - Handle 400 and 502 HTTP errors by displaying `st.error()`.
  - On success, render the `refined_goal`.
  - Render the `key_results` as a bulleted markdown list.
  - Display `confidence_score` using `st.metric()`.
  - Render "Save Approved Goal" button.
  - On click, send POST request to `http://localhost:8000/goals` and show `st.success()`.
- **Manual Verification:** Start backend (`uvicorn main:app`) and frontend (`streamlit run app.py`) locally and test the UI flow end-to-step.

## Phase 5: Live Evaluations
- **Evaluation Script (`test_evals.py`):**
  - Ensure script connects to the *actual* Gemini API (no mocks).
  - Tag tests with `@pytest.mark.integration`.
  - Add Happy Path Test 1: "I want to get better at public speaking." (Assert success, confidence >= 0.5, valid schema).
  - Add Happy Path Test 2: "Increase team velocity."
  - Add Happy Path Test 3: "Read more books."
  - Add Adversarial Test: "DROP TABLE goals;" (Assert valid JSON schema returned, but `confidence_score < 0.5`).
- **Run Evaluations:** Execute `pytest test_evals.py -v` to confirm real-world performance against the LLM.

## Phase 6: Dockerization
- **Backend Dockerfile (`Dockerfile.api`):**
  - Use `python:3.11-slim` base image.
  - Copy requirements and source code.
  - Expose port 8000.
  - Set CMD to ``.
- **Frontend Dockerfile (`Dockerfile.ui`):**
  - Use `python:3.11-slim` base image.
  - Copy requirements and source code.
  - Expose port 8501.
  - Set CMD to ``.
- **Orchestration (`docker-compose.yml`):**
  - Define `api` service (build from `Dockerfile.api`, map port 8000:8000).
  - Define `ui` service (build from `Dockerfile.ui`, map port 8501:8501).
  - Pass `GEMINI_API_KEY` from local `.env` file to the `api` service.
  - Pass `API_URL=http://api:8000` to the `ui` service.
  - Set up a named Docker volume to persist the SQLite `goals.db` file in the `api` service.
- **Final Launch:** Run `docker-compose up --build`.
- **Final Verification:** Access `http://localhost:8501`, test a goal, and verify logs show up in the Docker console.

## Backlog (from PR / Gemini review – to implement after brainstorming and planning)

- **Authentication and user-scoped goals (security):** The `GET /goals` endpoint returns all goal records without authentication or user-based filtering. In a multi-user environment this would allow any unauthenticated user to access other users’ goals (PII). **Remediation:** Implement an authentication mechanism (e.g. JWT, OAuth2), add a user reference to the `Goal` model, and update `GET /goals` (and `POST /goals` if needed) so that only goals belonging to the authenticated user are returned. Do this as a separate effort: brainstorm, then write an implementation plan, then implement.