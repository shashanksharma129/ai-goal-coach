# ABOUTME: Unit tests for auth: password hashing, validation, JWT create/decode.
# ABOUTME: Does not call the API; tests core.auth and config.

import pytest
from uuid import uuid4

from core.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password_length,
    validate_username,
    verify_password,
)


def test_hash_password_returns_different_each_time():
    """Hashing the same password twice yields different salts (secure)."""
    h1 = hash_password("samepassword")
    h2 = hash_password("samepassword")
    assert h1 != h2
    assert verify_password("samepassword", h1)
    assert verify_password("samepassword", h2)


def test_verify_password_accepts_correct_password():
    """Correct plain password matches its hash."""
    plain = "mySecretPass123"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_rejects_wrong_password():
    """Wrong plain password does not match hash."""
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_validate_password_length_accepts_long_enough():
    """Password meeting MIN_PASSWORD_LENGTH does not raise."""
    validate_password_length("a" * 8)
    validate_password_length("longpassword")


def test_validate_password_length_raises_for_short():
    """Password shorter than MIN_PASSWORD_LENGTH raises ValueError."""
    with pytest.raises(ValueError, match="at least"):
        validate_password_length("short")
    with pytest.raises(ValueError):
        validate_password_length("")


def test_validate_username_accepts_valid():
    """Non-empty username within length limit does not raise."""
    validate_username("alice")
    validate_username("a")


def test_validate_username_raises_empty():
    """Empty or whitespace-only username raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_username("")
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_username("   ")


def test_validate_username_raises_too_long():
    """Username over MAX_USERNAME_LENGTH raises ValueError."""
    from core.config import MAX_USERNAME_LENGTH
    with pytest.raises(ValueError, match="at most"):
        validate_username("a" * (MAX_USERNAME_LENGTH + 1))


def test_create_and_decode_access_token_roundtrip():
    """Token created for a user id decodes to the same id."""
    user_id = uuid4()
    token = create_access_token(user_id)
    decoded = decode_access_token(token)
    assert decoded == user_id


def test_decode_access_token_invalid_returns_none():
    """Invalid or malformed token decodes to None."""
    assert decode_access_token("not-a-jwt") is None
    assert decode_access_token("") is None
    assert decode_access_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJub3QtdXVpZCJ9.x") is None
