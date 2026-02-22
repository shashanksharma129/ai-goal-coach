# ABOUTME: Shared app configuration and constants used across API and UI (core package).
# ABOUTME: Keeps defaults in one place so API and clients stay in sync.

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_GOALS_PAGE_SIZE = 20
MAX_GOALS_PAGE_SIZE = 100

# Auth: read from env in production; defaults for dev only.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
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
