"""Smoke tests for the search endpoints + synonym expansion."""


def test_synonym_expand_programmer_to_engineer():
    """The headline requirement: searching 'programmer' should reach jobs
    titled 'software engineer'."""
    from app.services.synonyms import expand

    expanded = expand("programmer")
    assert "programmer" in expanded
    assert "software engineer" in expanded
    assert "developer" in expanded
    assert "coder" in expanded


def test_synonym_expand_multi_word_query():
    """'data analyst' (a multi-word title) should match its synset."""
    from app.services.synonyms import expand

    expanded = expand("data analyst")
    assert "business analyst" in expanded
    assert "bi analyst" in expanded


def test_synonym_expand_unknown_term_returns_self():
    """Unknown terms shouldn't crash — just return themselves."""
    from app.services.synonyms import expand

    assert expand("xyzzy") == {"xyzzy"}


def test_tsquery_or_handles_special_chars():
    """tsquery builder must strip Postgres-special characters."""
    from app.services.synonyms import to_tsquery_or

    out = to_tsquery_or({"c++", "node.js"})
    assert "|" in out  # OR-join present
    # No raw special chars that would break Postgres tsquery parsing
    assert "++" not in out
    # Phrase markers used for multi-word terms ("node js" → "node <-> js")
    assert "<->" in out


def test_job_search_endpoint_calls_search_crud(client, monkeypatch):
    """GET /job-postings should route through crud_search.search_jobs."""
    from app.crud import search as crud_search

    captured = {}

    def fake_search_jobs(db, **kw):
        captured.update(kw)
        return [], 0

    monkeypatch.setattr(crud_search, "search_jobs", fake_search_jobs)
    response = client.get("/job-postings?keyword=programmer&fuzzy=true&limit=5")
    assert response.status_code == 200
    assert captured["keyword"] == "programmer"
    assert captured["fuzzy"] is True
    assert captured["limit"] == 5


def test_candidate_search_requires_employer(client, monkeypatch):
    """/candidates/search is employer-only — without auth override, rejects."""
    from app.main import app
    from app.services.auth import (
        get_current_candidate,
        get_current_employer,
        get_current_user,
    )

    for dep in (get_current_candidate, get_current_employer, get_current_user):
        app.dependency_overrides.pop(dep, None)
    response = client.get("/candidates/search")
    assert response.status_code in (401, 403, 404)


def test_candidate_search_returns_page(client, monkeypatch):
    """Happy path: GET /candidates/search with employer auth returns paginated."""
    from app.crud import search as crud_search

    monkeypatch.setattr(
        crud_search, "search_candidates", lambda db, **kw: ([], 0)
    )
    response = client.get("/candidates/search?keyword=python&fuzzy=true")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
