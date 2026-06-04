"""Smoke tests for the memberships router."""
from unittest.mock import MagicMock


def test_get_me_synthesizes_when_no_row(client, monkeypatch):
    """When a candidate has never started checkout, /memberships/me returns
    a synthetic 'not a member' response (is_active=false)."""
    from app.crud import membership as crud_membership

    monkeypatch.setattr(crud_membership, "get_by_user_id", lambda db, uid: None)
    response = client.get("/memberships/me")
    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["membership_id"] is None
    assert body["stripe_subscription_id"] is None


def test_checkout_returns_url(client, monkeypatch):
    """POST /memberships/checkout should call stripe_client and return a URL."""
    from app.crud import membership as crud_membership
    from app.services import stripe_client as sc

    monkeypatch.setattr(crud_membership, "get_by_user_id", lambda db, uid: None)
    monkeypatch.setattr(
        sc, "create_customer", lambda **kw: "cus_TEST123"
    )
    monkeypatch.setattr(
        crud_membership,
        "upsert_customer",
        lambda db, **kw: MagicMock(stripe_customer_id="cus_TEST123"),
    )
    monkeypatch.setattr(
        sc,
        "create_checkout_session",
        lambda **kw: "https://checkout.stripe.com/c/pay/cs_test_123",
    )

    response = client.post("/memberships/checkout")
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://checkout.stripe.com/")


def test_portal_requires_existing_customer(client, monkeypatch):
    """POST /memberships/portal should 400 if no Stripe customer exists yet."""
    from app.crud import membership as crud_membership

    monkeypatch.setattr(crud_membership, "get_by_user_id", lambda db, uid: None)
    response = client.post("/memberships/portal")
    assert response.status_code == 400


def test_webhook_rejects_missing_signature(client):
    """No Stripe-Signature header → 400 invalid signature/payload."""
    response = client.post(
        "/webhooks/stripe", content=b'{"type":"test"}'
    )
    assert response.status_code == 400
