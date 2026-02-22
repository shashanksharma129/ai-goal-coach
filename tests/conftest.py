# ABOUTME: Pytest hooks and shared fixtures. Sets SECRET_KEY for tests before app/config load.
# ABOUTME: Loads .env so integration tests (e.g. test_evals) have GEMINI_API_KEY when run via pytest.

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Required by core.config before any test imports api.main.
os.environ.setdefault("SECRET_KEY", "test-secret-for-pytest")
