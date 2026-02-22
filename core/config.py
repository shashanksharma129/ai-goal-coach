# ABOUTME: Shared app configuration and constants used across API and UI (core package).
# ABOUTME: Keeps defaults in one place so API and clients stay in sync.

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_GOALS_PAGE_SIZE = 20
MAX_GOALS_PAGE_SIZE = 100

# Auth: SECRET_KEY must be set (e.g. in .env); no default to avoid JWT forgery in production.
_SECRET_KEY = os.environ.get("SECRET_KEY")
if not _SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable must be set. For local dev, add SECRET_KEY=your-secret to .env."
    )
SECRET_KEY = _SECRET_KEY
ALGORITHM = "HS256"
_DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60


def _parse_access_token_expire_minutes() -> int:
    raw = os.environ.get(
        "ACCESS_TOKEN_EXPIRE_MINUTES", str(_DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    try:
        return int(raw)
    except ValueError:
        return _DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES


ACCESS_TOKEN_EXPIRE_MINUTES = _parse_access_token_expire_minutes()
MIN_PASSWORD_LENGTH = 8
MIN_USERNAME_LENGTH = 1
MAX_USERNAME_LENGTH = 128

# CORS: comma-separated origins; default allows local Streamlit UI. Set in production.
_raw_cors = os.environ.get("CORS_ORIGINS", "http://localhost:8501")
CORS_ORIGINS = [o.strip() for o in _raw_cors.split(",") if o.strip()] or [
    "http://localhost:8501"
]
