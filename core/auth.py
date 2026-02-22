# ABOUTME: Password hashing and JWT creation/validation for API auth.
# ABOUTME: get_current_user dependency for FastAPI; use SECRET_KEY from config.

import bcrypt
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    MAX_USERNAME_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_USERNAME_LENGTH,
    SECRET_KEY,
)
from core.database import User, get_session

_http_bearer = HTTPBearer(auto_error=False)

# bcrypt truncates passwords at 72 bytes; we hash utf-8 bytes.
_BCRYPT_MAX_PASSWORD_BYTES = 72

# Pre-computed bcrypt hash for a constant string; used when user is None so login
# always runs verify_password (constant-time, prevents username enumeration).
DUMMY_PASSWORD_HASH = "$2b$12$DbmI/yRDB5j9Q8I7R9cb5.9jZPh/c32i4pA35t4vTf2jdq32n.L.S"


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password (UTF-8, truncated at 72 bytes)."""
    raw = plain.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_PASSWORD_BYTES:
        raw = raw[:_BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plain password matches the hash."""
    raw = plain.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_PASSWORD_BYTES:
        raw = raw[:_BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(raw, hashed.encode("ascii"))


def validate_password_length(password: str) -> None:
    """Raise ValueError if password is shorter than MIN_PASSWORD_LENGTH."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")


def validate_username(username: str) -> None:
    """Raise ValueError if username is empty or too long."""
    u = username.strip()
    if len(u) < MIN_USERNAME_LENGTH:
        raise ValueError("Username cannot be empty")
    if len(u) > MAX_USERNAME_LENGTH:
        raise ValueError(f"Username must be at most {MAX_USERNAME_LENGTH} characters")


def create_access_token(user_id: UUID) -> str:
    """Build a JWT with sub=user_id and exp set from ACCESS_TOKEN_EXPIRE_MINUTES."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID | None:
    """Decode the JWT and return the subject (user id) or None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        return UUID(sub)
    except (JWTError, ValueError):
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
) -> User:
    """FastAPI dependency: require Authorization Bearer token and return the User or 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    with get_session() as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
