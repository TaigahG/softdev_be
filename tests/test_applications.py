"""Smoke tests for the applications router."""


def test_list_my_applications_returns_list(client, monkeypatch):
    from app.crud import application as crud_application

    monkeypatch.setattr(
        crud_application, "list_for_candidate", lambda db, cid: []
    )
    response = client.get("/applications/me")
    assert response.status_code == 200
    assert response.json() == []


def test_duplicate_apply_returns_409(client, monkeypatch):
    """The unique constraint surfaces as 409."""
    from app.crud import application as crud_application

    def raise_duplicate(db, *, candidate_id, data):
        raise crud_application.DuplicateApplicationError()

    monkeypatch.setattr(crud_application, "create", raise_duplicate)
    response = client.post(
        "/applications", json={"candidate_id": 1, "job_id": 42}
    )
    assert response.status_code == 409
