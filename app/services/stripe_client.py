"""Stripe API wrapper for candidate membership subscriptions.

Env vars (all required for the membership feature to work):
    STRIPE_SECRET_KEY       — sk_test_... (dev) or sk_live_... (prod)
    STRIPE_WEBHOOK_SECRET   — from `stripe listen` (dev) or Dashboard endpoint (prod)
    STRIPE_PRICE_ID         — the recurring Price ID
    STRIPE_SUCCESS_URL      — frontend route after checkout success
    STRIPE_CANCEL_URL       — frontend route if user backs out
"""
import os
from typing import Any
from uuid import UUID

import stripe


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set in .env")
    return value


def _configured() -> None:
    """Set the API key on the module. Cheap to call repeatedly."""
    stripe.api_key = _require_env("STRIPE_SECRET_KEY")


def create_customer(
    *, email: str, name: str, candidate_id: int, user_id: UUID
) -> str:
    """Create a Stripe Customer for this candidate; return its ID."""
    _configured()
    customer = stripe.Customer.create(
        email=email or None,
        name=name,
        metadata={
            "candidate_id": str(candidate_id),
            "user_id": str(user_id),
        },
    )
    return customer.id


def create_checkout_session(*, customer_id: str, candidate_id: int) -> str:
    """Create a Checkout Session and return the URL the frontend redirects to."""
    _configured()
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[
            {"price": _require_env("STRIPE_PRICE_ID"), "quantity": 1}
        ],
        success_url=_require_env("STRIPE_SUCCESS_URL"),
        cancel_url=_require_env("STRIPE_CANCEL_URL"),
        # Defaults: cancel_at_period_end=False on creation; user can toggle via Portal.
        metadata={"candidate_id": str(candidate_id)},
        subscription_data={"metadata": {"candidate_id": str(candidate_id)}},
    )
    if not session.url:
        raise RuntimeError("Stripe returned a Checkout Session without a URL")
    return session.url


def create_portal_session(*, customer_id: str) -> str:
    """Create a Customer Portal session — Stripe-hosted self-service for the user
    to update payment method, change plan, cancel, etc."""
    _configured()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=_require_env("STRIPE_SUCCESS_URL"),
    )
    return session.url


def retrieve_subscription(subscription_id: str) -> Any:
    """Fetch a subscription's current state from Stripe.

    Used by webhook handlers that receive only an ID (e.g.
    invoice.payment_succeeded carries `subscription` as a string)."""
    _configured()
    return stripe.Subscription.retrieve(subscription_id)


def construct_event(payload: bytes, sig_header: str) -> Any:
    """Verify the webhook signature and parse the event.

    Raises stripe.SignatureVerificationError on bad sig, ValueError on bad payload.
    """
    _configured()
    return stripe.Webhook.construct_event(
        payload, sig_header, _require_env("STRIPE_WEBHOOK_SECRET")
    )
