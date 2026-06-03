"""Shared fixtures for smoke tests.

These tests don't touch a real database — `get_db` is overridden to a MagicMock,
and CRUD calls are monkeypatched per test. The goal is to verify router wiring,
auth dependency injection, request validation, and response serialization.

Run with:
    TESTING=1 DATABASE_URL=postgresql://x SUPABASE_URL=https://x.supabase.co \
        pytest tests/ -v
"""
import os
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Set required env vars BEFORE importing the app — otherwise app.database raises
# on missing DATABASE_URL, and the test session won't even start.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://test:test@localhost/test"
)
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Candidate, Employer  # noqa: E402
from app.services.auth import (  # noqa: E402
    AuthUser,
    get_current_candidate,
    get_current_employer,
    get_current_user,
)


@pytest.fixture
def fake_db():
    return MagicMock()


@pytest.fixture
def fake_candidate():
    c = Candidate(candidate_id=1, user_id=uuid4(), full_name="Test Candidate")
    return c


@pytest.fixture
def fake_employer():
    e = Employer(
        employer_id=1,
        user_id=uuid4(),
        full_name="Test Boss",
        company_name="Acme Co",
    )
    return e


@pytest.fixture
def client(fake_db, fake_candidate, fake_employer):
    """TestClient with auth + db deps overridden. Default identities are
    `fake_candidate` and `fake_employer`; override per test as needed."""
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_candidate] = lambda: fake_candidate
    app.dependency_overrides[get_current_employer] = lambda: fake_employer
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        user_id=fake_candidate.user_id, email="test@example.com", metadata={}
    )
    yield TestClient(app)
    app.dependency_overrides.clear()
