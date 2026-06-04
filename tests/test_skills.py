"""Smoke tests for the skill autocomplete endpoint."""


def test_skills_autocomplete_returns_list(client, monkeypatch):
    from app.crud import skill as crud_skill

    monkeypatch.setattr(
        crud_skill, "search", lambda db, q, limit=20: []
    )
    response = client.get("/skills?q=pyt")
    assert response.status_code == 200
    assert response.json() == []


def test_skills_endpoint_is_public(client, monkeypatch):
    """No auth header required."""
    from app.crud import skill as crud_skill

    monkeypatch.setattr(
        crud_skill, "search", lambda db, q, limit=20: []
    )
    response = client.get("/skills?q=python")
    assert response.status_code == 200
