# ABOUTME: Pydantic models for AI output contract (GoalModel).
# ABOUTME: Used by ADK agent and FastAPI request/response bodies.

from pydantic import BaseModel, Field


class GoalModel(BaseModel):
    """Structured output from the goal-refinement agent."""

    refined_goal: str = Field(
        description="The SMART version of the user's goal."
    )
    key_results: list[str] = Field(
        description="3 to 5 measurable key results.",
        min_length=3,
        max_length=5,
    )
    confidence_score: float = Field(
        description="Confidence that input is a valid goal.",
        ge=0.0,
        le=1.0,
    )
