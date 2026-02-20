# ABOUTME: FastAPI app: POST /generate (goal refinement) and POST /goals (persist).
# ABOUTME: 400 on low confidence, 502 on agent/schema failure.

import json
import logging
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from goal_coach.agent import generate_smart_goal
from database import Goal, get_session
from schemas import GoalModel

app = FastAPI(title="AI Goal Coach API")
# allow_origins=["*"] is for prototype/dev only; set explicit origins before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    user_input: str


class GoalCreateRequest(BaseModel):
    original_input: str
    refined_goal: str
    key_results: list[str] = Field(min_length=3, max_length=5)
    confidence_score: float = Field(ge=0.0, le=1.0)
    status: str = "draft"


@app.post("/generate", response_model=GoalModel)
def post_generate(req: GenerateRequest):
    """Generate a refined SMART goal from vague user input."""
    try:
        result = generate_smart_goal(req.user_input)
    except Exception:
        logging.exception("generate_smart_goal failed")
        return JSONResponse(
            status_code=502,
            content={"message": "AI model failed to generate a valid response."},
        )
    if result.confidence_score < 0.5:
        return JSONResponse(
            status_code=400,
            content={"message": "Input too vague or invalid to generate a goal."},
        )
    return result


@app.post("/goals")
def post_goals(req: GoalCreateRequest):
    """Persist an approved goal to the database."""
    with get_session() as session:
        goal = Goal(
            original_input=req.original_input,
            refined_goal=req.refined_goal,
            key_results=json.dumps(req.key_results),
            confidence_score=req.confidence_score,
            status=req.status,
        )
        session.add(goal)
        session.commit()
        session.refresh(goal)
        return {
            "id": str(goal.id),
            "original_input": goal.original_input,
            "refined_goal": goal.refined_goal,
            "key_results": json.loads(goal.key_results),
            "confidence_score": goal.confidence_score,
            "status": goal.status,
            "created_at": goal.created_at.isoformat(),
        }
