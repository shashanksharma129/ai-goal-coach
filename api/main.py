# ABOUTME: FastAPI app: POST /generate (goal refinement), POST /goals (persist), GET /goals (list, paginated).
# ABOUTME: 400 on low confidence, 502 on agent/schema failure. Auth via JWT; goals scoped by user.

import json
import logging

from fastapi import APIRouter, Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import select

from core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    DUMMY_PASSWORD_HASH,
    validate_password_length,
    validate_username,
    verify_password,
)
from core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    CORS_ORIGINS,
    DEFAULT_GOALS_PAGE_SIZE,
    MAX_GOALS_PAGE_SIZE,
)
from core.database import Goal, User, get_session
from core.schemas import GoalModel
from goal_coach.agent import generate_smart_goal

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupResponse(BaseModel):
    id: str
    username: str
    access_token: str
    token_type: str
    expires_in: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


@auth_router.post("/signup", status_code=201, response_model=SignupResponse)
def post_signup(req: SignupRequest):
    """Create a new user and return an access token so the client can skip calling login."""
    try:
        validate_username(req.username)
        validate_password_length(req.password)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"message": str(e)})
    username_clean = req.username.strip()
    try:
        with get_session() as session:
            user = User(
                username=username_clean,
                password_hash=hash_password(req.password),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            access_token = create_access_token(user.id)
            return SignupResponse(
                id=str(user.id),
                username=user.username,
                access_token=access_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
    except IntegrityError:
        return JSONResponse(
            status_code=409,
            content={"message": "Username already taken."},
        )
    except SQLAlchemyError:
        logging.exception("post_signup failed (database error)")
        return JSONResponse(
            status_code=500,
            content={"message": "Could not create account."},
        )


@auth_router.post("/login", response_model=LoginResponse)
def post_login(req: LoginRequest):
    """Authenticate and return a JWT. Uses constant-time password check to avoid username enumeration."""
    with get_session() as session:
        stmt = select(User).where(User.username == req.username.strip())
        user = session.exec(stmt).first()
    password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    if not verify_password(req.password, password_hash) or user is None:
        return JSONResponse(
            status_code=401,
            content={"message": "Invalid username or password."},
        )
    access_token = create_access_token(user.id)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _goal_to_json(goal: Goal) -> dict:
    """Serialize a Goal row to the same dict shape as POST /goals response."""
    return {
        "id": str(goal.id),
        "original_input": goal.original_input,
        "refined_goal": goal.refined_goal,
        "key_results": json.loads(goal.key_results) if goal.key_results else [],
        "confidence_score": goal.confidence_score,
        "status": goal.status,
        "created_at": goal.created_at.isoformat(),
    }


app = FastAPI(title="AI Goal Coach API")
app.include_router(auth_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
def post_generate(req: GenerateRequest, _user: User = Depends(get_current_user)):
    """Generate a refined SMART goal from vague user input. Requires authentication."""
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
def post_goals(req: GoalCreateRequest, current_user: User = Depends(get_current_user)):
    """Persist an approved goal to the database. Goal is scoped to the authenticated user."""
    try:
        with get_session() as session:
            goal = Goal(
                user_id=current_user.id,
                original_input=req.original_input,
                refined_goal=req.refined_goal,
                key_results=json.dumps(req.key_results),
                confidence_score=req.confidence_score,
                status=req.status,
            )
            session.add(goal)
            session.commit()
            session.refresh(goal)
            return _goal_to_json(goal)
    except SQLAlchemyError:
        logging.exception("post_goals failed (database error)")
        return JSONResponse(
            status_code=500,
            content={"message": "Could not save goal."},
        )
    except Exception:
        logging.exception("post_goals: unexpected error (non-SQLAlchemy)")
        return JSONResponse(
            status_code=500,
            content={"message": "An unexpected error occurred while saving the goal."},
        )


@app.get("/goals")
def get_goals(
    limit: int = Query(DEFAULT_GOALS_PAGE_SIZE, ge=0, le=MAX_GOALS_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """List saved goals for the authenticated user, newest first. Returns { goals: [...], total: N }."""
    try:
        with get_session() as session:
            total_stmt = (
                select(func.count())
                .select_from(Goal)
                .where(Goal.user_id == current_user.id)
            )
            total = session.exec(total_stmt).one()
            stmt = (
                select(Goal)
                .where(Goal.user_id == current_user.id)
                .order_by(Goal.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            goals = list(session.exec(stmt))
        return {"goals": [_goal_to_json(g) for g in goals], "total": total}
    except SQLAlchemyError:
        logging.exception("get_goals failed (database error)")
        return JSONResponse(
            status_code=500,
            content={"message": "Could not load goals."},
        )
    except Exception:
        logging.exception("get_goals failed unexpectedly")
        return JSONResponse(
            status_code=500,
            content={"message": "An unexpected error occurred while loading goals."},
        )
