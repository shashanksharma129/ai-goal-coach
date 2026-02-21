

# AI GOAL COACH – SYSTEM SPECIFICATION (v2.0 - Final)

## 1. Executive Summary & Core Principles

The AI Goal Coach is a lightweight, containerized system that refines vague employee aspirations into structured SMART goals.

**Core Design Principles:**

1. **Contract Enforcement via ADK:** The LLM's output must match a strict schema. We will use Google ADK's `LlmAgent` with a defined `output_schema` to natively force the model to return valid JSON.
2. **Ruthless Simplicity (Prototype Scope):** To prove the core AI architecture without scope creep, the system uses a single-agent pattern, a local SQLite database, and omits heavy authentication layers.
3. **Observability by Default:** Telemetry is not an afterthought. Every AI call will capture latency, token usage, and calculated cost via ADK's OpenTelemetry (OTel) integration.

---

## 2. Architecture & Tech Stack

**Tech Stack:**

* **Frontend:** Streamlit (Python)
* **Backend / API:** FastAPI (Python)
* **AI Framework:** Google Agent Development Kit (ADK) Python SDK
* **AI Model:** `gemini-2.5-flash` (via Google AI Studio free tier)
* **Database:** SQLite (local file)
* **Deployment:** Docker (two containers: Frontend and Backend)

**High-Level Flow:**

1. User enters a vague goal in the Streamlit UI.
2. Streamlit sends a JSON HTTP POST request to the FastAPI backend.
3. FastAPI triggers the ADK `Runner` connected to an `LlmAgent`.
4. The `LlmAgent` communicates with the Gemini model, enforcing the Pydantic schema.
5. A custom ADK telemetry callback logs the execution metrics and cost to standard output.
6. FastAPI returns the structured JSON to the frontend to be rendered and optionally saved to SQLite.

---

## 3. Data Handling & Schema

To avoid the overhead of PostgreSQL and Alembic in a prototype, we are using a simple SQLite database with standard SQL queries or a lightweight ORM (like SQLModel).

**SQLite Table: `goals**`

* `id` (UUID, Primary Key)
* `original_input` (TEXT)
* `refined_goal` (TEXT)
* `key_results` (TEXT/JSON) - Stores the array of strings
* `confidence_score` (REAL) - Float between 0.0 and 1.0
* `status` (TEXT) - e.g., 'draft', 'saved', 'archived'
* `created_at` (TIMESTAMP)

**AI Output Contract (Pydantic Model for ADK):**

```python
from pydantic import BaseModel, Field

class GoalModel(BaseModel):
    refined_goal: str = Field(description="The SMART version of the user's goal.")
    key_results: list[str] = Field(description="3 to 5 measurable key results.", min_length=3, max_length=5)
    confidence_score: float = Field(description="Confidence that input is a valid goal (0.0 to 1.0)", ge=0.0, le=1.0)

```

---

## 4. AI Integration & Guardrails

**Agent Configuration:**

* We will instantiate a single `LlmAgent` from `google.adk.agents`.
* The `output_schema` parameter of the agent will be set to the `GoalModel` Pydantic class to guarantee structured JSON output.
* We explicitly reject the `LoopAgent` or multi-agent patterns to minimize token usage and latency for this straightforward transformation task.

**Error Handling & Guardrail Strategy:**

1. **Fail-Fast on Low Confidence:** If the AI successfully returns a JSON payload but the `confidence_score` is `< 0.5` (e.g., the user typed "kjsfdkj"), the backend will **immediately** return a `400 Bad Request` to the frontend with an error envelope (`"message": "Input too vague or invalid to generate a goal."`). It will *not* retry.
2. **Retry on Schema Failure:** If the LLM hallucinates and fails to conform to the `GoalModel` schema, ADK's internal execution engine will handle the retry mechanism automatically. If it ultimately fails, FastAPI will catch the ADK exception and return a `502 Bad Gateway` (`"message": "AI model failed to generate a valid response."`).

---

## 5. Observability & Telemetry

The system must log the inputs, outputs, latency, and token cost of every AI request without cluttering the core business logic.

* **OTel Integration:** We will use ADK's built-in OpenTelemetry hooks to trace the agent's execution span.
* **Custom Logging Callback:** We will attach a telemetry listener to the ADK `Runner`. On completion of the `LlmAgent` run, this listener will extract the metadata and print a structured JSON log to `stdout`.
* **Cost Calculation:** The logger will calculate estimated cost based on Gemini 2.5 Flash API pricing:
* `Estimated Cost = (prompt_tokens * $PricePerToken) + (completion_tokens * $PricePerToken)`


* **Log Structure:** `{"timestamp": "...", "latency_ms": 1200, "prompt_tokens": 45, "completion_tokens": 120, "estimated_cost_usd": 0.000015, "confidence_score": 0.92, "success": true}`

---

## 6. Testing & Evaluation Plan

The evaluation script (`test_evals.py`) acts as our CI gate to ensure model/prompt changes do not break the system.

**Mini-Eval Setup:**
We will use ADK's native testing/evaluation capabilities (or a simple pytest script) to pass predefined inputs to the `LlmAgent` and assert the structural integrity of the output.

**Test Cases:**

1. **Happy Path 1:** `"I want to get better at public speaking."` -> *Assert success, confidence >= 0.5, valid schema.*
2. **Happy Path 2:** `"Increase team velocity."` -> *Assert success, confidence >= 0.5, valid schema.*
3. **Happy Path 3:** `"Read more books."` -> *Assert success, confidence >= 0.5, valid schema.*
4. **Adversarial / Edge Case:** `"DROP TABLE goals;"` (SQL Injection attempt) or `"asdfghjkl"` -> *Assert the schema is perfectly valid JSON, but the `confidence_score` is STRICTLY `< 0.5`.*

---

## 7. Scaling to 10,000 Users (ADR Note)

While the prototype relies on SQLite and synchronous HTTP requests, moving to production would require:

1. Replacing SQLite with a connection-pooled Cloud SQL database (PostgreSQL).
2. Deploying the ADK agent to Vertex AI Agent Engine for managed, scalable runtime execution.
3. Shifting to an asynchronous task queue (e.g., Celery/Redis) so the UI polls for the AI response rather than holding HTTP connections open during LLM latency spikes.

