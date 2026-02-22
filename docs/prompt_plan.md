
This document is a historical blueprint for code-generation prompts. The repository now uses the layout `api/`, `ui/`, `core/`, `goal_coach/` (see docs/plans/); references to `main.py` and `app.py` correspond to `api/main.py` and `ui/app.py`.

Here is the detailed blueprint, the iterative breakdown process, and the final sequence of prompts to feed into a code-generation LLM. 

### Phase 1: High-Level Blueprint Draft
Before writing code, we need to understand the structural pillars of the application.
1.  **Core Data & Schemas:** Pydantic models (for the AI output) and SQLite models (for persistence).
2.  **AI & Telemetry Layer:** Wrapping the Google ADK `LlmAgent`, defining the prompt/schema, and injecting OpenTelemetry/logging hooks.
3.  **API Layer (FastAPI):** Exposing the AI generation and database persistence as HTTP endpoints, with specific business logic (e.g., `< 0.5` confidence triggers a `400 Bad Request`).
4.  **Frontend Layer (Streamlit):** A simple UI to take user input, call the API, and display results.
5.  **Quality Assurance:** An evaluation script (`test_evals.py`) testing live LLM outputs against our Pydantic schema.
6.  **Infrastructure:** Docker containerization to run the FastAPI backend and Streamlit frontend together.

### Phase 2: Iterative Breakdown (Right-Sizing for TDD)
*Round 1 Review:* Building the whole API or the whole AI layer in one prompt is too risky. If the LLM hallucinates the ADK integration, the API will fail. We need to split the data layer, the AI layer, and the API layer into strictly testable chunks.

*Round 2 Review:* Let's sequence it so that **no code is orphaned**. 
*   **Step 1:** Establish the data models (Pydantic schema + SQLite/SQLModel DB). Test: In-memory DB CRUD.
*   **Step 2:** Build the AI Agent & Telemetry wrapper using the ADK. Test: Mock the LLM to ensure the ADK runner and telemetry callbacks execute and format logs correctly.
*   **Step 3:** Build the FastAPI endpoints. Wire Step 1 (DB) and Step 2 (Agent) into the routes. Test: Use `TestClient` to test the HTTP 400 logic on low confidence and HTTP 502 on model failure.
*   **Step 4:** Build the Streamlit Frontend. Test: Manual/mocked HTTP requests to ensure UI rendering works.
*   **Step 5:** Build the Evaluation script (`test_evals.py`) to run real data through the system.
*   **Step 6:** Dockerize the completed, tested application.

This chunking is perfectly sized. Each step relies on the successful completion of the previous step, enforces Test-Driven Development (TDD), and handles complex concepts (like ADK telemetry) in isolation before wrapping them in an API.

---

### Phase 3: The LLM Code-Generation Prompts

Below is the sequenced set of prompts to copy/paste into your preferred code-generation LLM (e.g., ChatGPT, Claude, GitHub Copilot).

#### Step 1: Data Models & Database Setup
```text
You are an expert Python developer practicing Test-Driven Development (TDD). We are building an "AI Goal Coach" application.

Please execute Step 1 of our project: Data Models & Database Setup.

Requirements:
1. Create a virtual environment setup guide or a `requirements.txt` containing: `fastapi`, `uvicorn`, `sqlmodel`, `pydantic`, `pytest`, `pytest-asyncio`.
2. Create `schemas.py`: Define a Pydantic model named `GoalModel` that represents our AI output contract. It must contain:
   - `refined_goal`: str (Description: "The SMART version of the user's goal.")
   - `key_results`: list (Description: "3 to 5 measurable key results.", min_length=3, max_length=5)
   - `confidence_score`: float (Description: "Confidence that input is a valid goal", ge=0.0, le=1.0)
3. Create `database.py`: Use `SQLModel` to define a `Goal` table. It should have:
   - `id`: UUID (Primary key, default `uuid4`)
   - `original_input`: str
   - `refined_goal`: str
   - `key_results`: str (Store the list of strings as a JSON string)
   - `confidence_score`: float
   - `status`: str (Default: 'draft')
   - `created_at`: datetime (Default: UTC now)
   Also include a function `get_session()` to yield an SQLite session.
4. Create `test_database.py`: Write `pytest` tests using an in-memory SQLite database (`sqlite:///:memory:`) to verify that the `Goal` model can be created, saved, and retrieved successfully. 

Output the code for these files cleanly, ensuring all tests pass.
```

#### Step 2: Google ADK Agent & Telemetry
```text
Building upon our previous step, please execute Step 2: AI Agent Core & Telemetry.

We are using the Google Agent Development Kit (ADK) Python SDK. 

Requirements:
1. Create `telemetry.py`: Define a custom logging callback/listener class for the ADK `Runner`. When an execution finishes, it must print a structured JSON log to standard output. 
   - The log must contain: `timestamp`, `latency_ms`, `prompt_tokens`, `completion_tokens`, `estimated_cost_usd`, `confidence_score`, and `success` (boolean).
   - Assume Gemini 2.5 Flash pricing for the cost calculation (e.g., $0.075 per 1M prompt tokens, $0.30 per 1M completion tokens).
2. Create `agent.py`: 
   - Import `LlmAgent` and `Runner` from `google.adk.agents` and `google.adk.runners`.
   - Instantiate an `LlmAgent` using the `gemini-2.5-flash` model. 
   - Crucially, configure the agent with `output_schema=GoalModel` (importing `GoalModel` from `schemas.py` created in Step 1) to force structured JSON output.
   - Create a function `generate_smart_goal(user_input: str) -> GoalModel` that uses the ADK `Runner` to execute the agent, passing your telemetry callback from `telemetry.py` to the runner.
3. Create `test_agent.py`: Write `pytest` tests to verify `generate_smart_goal`. Use `unittest.mock` to mock the ADK `Runner` and `LlmAgent` so we don't make real API calls during unit tests. Verify that the telemetry JSON logger is invoked correctly.

Output the code for `telemetry.py`, `agent.py`, and `test_agent.py`.
```

#### Step 3: FastAPI Backend
```text
Building on `schemas.py`, `database.py`, and `agent.py`, please execute Step 3: FastAPI Backend Integration.

Requirements:
1. Create `main.py`: Initialize a FastAPI app. 
2. Create Endpoint 1: `POST /generate`. 
   - Accepts a JSON body `{"user_input": "..."}`.
   - Calls `generate_smart_goal(user_input)` from `agent.py`.
   - Business Logic Guardrail 1: If the returned `GoalModel` has a `confidence_score < 0.5`, immediately return a `400 Bad Request` with `{"message": "Input too vague or invalid to generate a goal."}`. Do NOT save to DB.
   - Business Logic Guardrail 2: Catch any schema/ADK generation exceptions and return a `502 Bad Gateway` with `{"message": "AI model failed to generate a valid response."}`.
   - If successful, return the `GoalModel` as JSON.
3. Create Endpoint 2: `POST /goals`.
   - Accepts the final approved goal data (similar to GoalModel, plus original_input) and saves it to the SQLite database using the `Goal` SQLModel from `database.py`. Returns the database record.
4. Create `test_main.py`: Write tests using `fastapi.testclient.TestClient`. Mock `generate_smart_goal`. 
   - Test a successful `/generate` response.
   - Test the `400` logic by mocking a `GoalModel` return with `confidence_score = 0.2`.
   - Test the `502` logic by mocking an ADK exception.
   - Test the `/goals` endpoint to ensure it persists to the mocked DB.

Output the code for `main.py` and `test_main.py`.
```

#### Step 4: Streamlit Frontend
```text
Now that our FastAPI backend is fully tested and working, please execute Step 4: Streamlit Frontend.

Requirements:
1. Add `streamlit` and `requests` to our dependency list.
2. Create `app.py`: A Streamlit UI that interacts with our FastAPI backend running at `http://localhost:8000`.
3. UI Flow:
   - Display a title: "AI Goal Coach".
   - Render a `st.text_area` for the user to input a vague goal.
   - Render a "Refine Goal" button. When clicked, it makes a POST request to the backend's `/generate` endpoint.
   - Handle backend errors cleanly: If it receives a 400 or 502, display a `st.error` using the message returned from the API.
   - If successful, display the `refined_goal`, the `key_results` as a bulleted list, and the `confidence_score` using a `st.metric`.
   - Show a "Save Approved Goal" button. When clicked, make a POST request to `/goals` to persist the data, and show a `st.success` message upon completion.

Output the code for `app.py`. Keep it clean, intuitive, and user-friendly.
```

#### Step 5: Live Evaluations
```text
Our core system is complete. Please execute Step 5: Evaluation Script.

We need an evaluation script to run live integration tests against the actual LLM to ensure prompt/model changes don't break our application.

Requirements:
1. Create `test_evals.py`. This script should use `pytest` but connect directly to `generate_smart_goal` from `agent.py` (making real network calls to Gemini, so assume `GEMINI_API_KEY` is in the environment).
2. Implement the 4 specified test cases:
   - Happy Path 1: "I want to get better at public speaking." -> Assert success, confidence >= 0.5, valid schema.
   - Happy Path 2: "Increase team velocity." -> Assert success, confidence >= 0.5, valid schema.
   - Happy Path 3: "Read more books." -> Assert success, confidence >= 0.5, valid schema.
   - Adversarial Case: "DROP TABLE goals;" -> Assert the schema parses validly as JSON into `GoalModel`, but assert that `confidence_score` is STRICTLY `< 0.5`.

Output `test_evals.py` configured with appropriate pytest marks (e.g., `@pytest.mark.integration` or `@pytest.mark.slow`) so they don't run accidentally during standard CI unit testing.
```

#### Step 6: Dockerization
```text
Finally, please execute Step 6: Dockerization. We need to deploy this prototype easily.

Requirements:
1. Create `Dockerfile.api`: A Dockerfile that installs dependencies, sets up the FastAPI code, and runs it via `uvicorn` on port 8000. Ensure it uses a lightweight python base image (e.g., `python:3.11-slim`).
2. Create `Dockerfile.ui`: A Dockerfile for the Streamlit app. It should run on port 8501. 
3. Create `docker-compose.yml`: Wire both containers together. 
   - The UI container should be able to communicate with the API container via an environment variable (e.g., `API_URL=http://api:8000`).
   - Map port 8501 to the host so the user can access the Streamlit UI.
   - Ensure `GEMINI_API_KEY` can be passed through to the API container.
   - Include a Docker volume for the SQLite database so data persists between container restarts.

Provide the contents of all three files.
```