# ABOUTME: Pytest hooks and shared fixtures. Sets SECRET_KEY for tests before app/config load.

import os

# Required by core.config before any test imports api.main.
os.environ.setdefault("SECRET_KEY", "test-secret-for-pytest")
