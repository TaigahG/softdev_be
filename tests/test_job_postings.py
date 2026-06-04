"""Smoke tests for the job-postings router."""
from app.main import app
from app.services.auth import (
    get_current_candidate,
    get_current_employer,
    get_current_user,
)


def test_list_jobs_is_public(client, monkeypatch):
    """GET /job-postings should not require auth."""
    from app.crud import search as crud_search

    monkeypatch.setattr(
        crud_search, "search_jobs", lambda db, **kw: ([], 0)
    )
    response = client.get("/job-postings?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "total": 0, "limit": 10, "offset": 0}


def test_create_job_requires_employer(client):
    """POST /job-postings without ANY auth override should reject. Pop the
    whole chain — get_current_employer depends on get_current_user."""
    for dep in (get_current_candidate, get_current_employer, get_current_user):
        app.dependency_overrides.pop(dep, None)
    response = client.post("/job-postings", json={"title": "X"})
    assert response.status_code in (401, 403, 404)


def test_get_unknown_job_404(client, monkeypatch):
    from app.crud import job_posting as crud_job

    monkeypatch.setattr(crud_job, "get", lambda db, jid: None)
    response = client.get("/job-postings/999")
    assert response.status_code == 404
