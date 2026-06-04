"""Smoke tests for the candidates router.

These don't exercise real SQL — `get_db` is a MagicMock and CRUD is
monkeypatched. The goal is to verify wiring + auth gates.
"""
from app.main import app
from app.services.auth import (
    get_current_candidate,
    get_current_employer,
    get_current_user,
)


def test_get_my_resumes_returns_list(client, monkeypatch):
    """Happy-path: list endpoint with monkeypatched CRUD returns []."""
    from app.crud import candidate as crud_candidate

    monkeypatch.setattr(crud_candidate, "list_resumes", lambda db, cid: [])
    response = client.get("/candidates/me/resumes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_work_experiences_returns_list(client, monkeypatch):
    from app.crud import work_experience as crud_we

    monkeypatch.setattr(crud_we, "list_for_candidate", lambda db, cid: [])
    response = client.get("/candidates/me/work-experiences")
    assert response.status_code == 200
    assert response.json() == []


def test_patch_my_profile_calls_crud(client, monkeypatch, fake_candidate):
    """PATCH /candidates/me should call crud.update with our data + return the
    response shape. We bypass full ORM serialization by stubbing crud.update
    to return a dict-compatible object."""
    from app.crud import candidate as crud_candidate

    called = {}

    def fake_update(db, *, candidate, data):
        called["data"] = data.model_dump(exclude_unset=True)
        return candidate

    monkeypatch.setattr(crud_candidate, "update", fake_update)
    monkeypatch.setattr(crud_candidate, "latest_resume_url", lambda db, cid: None)

    # CandidateOut requires created_at/updated_at + lists — patch the
    # serializer to skip Pydantic conversion of the ORM object.
    from app.routers import candidates as candidates_router

    monkeypatch.setattr(
        candidates_router,
        "_to_out",
        lambda db, c: {
            "candidate_id": c.candidate_id,
            "user_id": str(c.user_id),
            "full_name": c.full_name,
            "skills": [],
            "work_experiences": [],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    )

    response = client.patch(
        "/candidates/me",
        json={"biography": "Hi", "skills": ["Python", "AWS"]},
    )
    assert response.status_code == 200
    assert called["data"] == {
        "biography": "Hi",
        "skills": ["Python", "AWS"],
    }


def test_get_my_profile_requires_auth(client):
    """Without ANY auth override, /candidates/me should reject. Need to pop
    the entire auth chain — `get_current_candidate` depends on
    `get_current_user`, which is also overridden by the fixture."""
    for dep in (get_current_candidate, get_current_employer, get_current_user):
        app.dependency_overrides.pop(dep, None)
    response = client.get("/candidates/me")
    # 401 (no token) or 403 (forbidden) — either is acceptable auth rejection.
    assert response.status_code in (401, 403)
