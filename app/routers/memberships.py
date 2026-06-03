"""Membership router — candidate-only subscription via Stripe."""
import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.crud import membership as crud_membership
from app.database import get_db
from app.models import Candidate, Membership
from app.schemas import (
    MembershipCheckoutOut,
    MembershipOut,
    MembershipPortalOut,
)
from app.services import stripe_client
from app.services.auth import AuthUser, get_current_candidate, get_current_user

log = logging.getLogger(__name__)

# Two routers in one file: candidate-facing endpoints (auth-gated, /memberships
# prefix) and the public webhook (signature-verified, /webhooks/stripe path).
router = APIRouter(prefix="/memberships", tags=["memberships"])
webhook_router = APIRouter(tags=["stripe-webhook"])


# ─────────────────────────── candidate endpoints ───────────────────────────


@router.post("/checkout", response_model=MembershipCheckoutOut)
def create_checkout(
    candidate: Candidate = Depends(get_current_candidate),
    auth: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MembershipCheckoutOut:
    """Create a Stripe Checkout Session and return the redirect URL."""
    membership = crud_membership.get_by_user_id(db, candidate.user_id)
    customer_id = membership.stripe_customer_id if membership else None

    if not customer_id:
        customer_id = stripe_client.create_customer(
            email=auth.email or "",
            name=candidate.full_name,
            candidate_id=candidate.candidate_id,
            user_id=candidate.user_id,
        )
        crud_membership.upsert_customer(
            db,
            user_id=candidate.user_id,
            stripe_customer_id=customer_id,
        )

    url = stripe_client.create_checkout_session(
        customer_id=customer_id,
        candidate_id=candidate.candidate_id,
    )
    return MembershipCheckoutOut(url=url)


@router.get("/me", response_model=MembershipOut)
def get_my_membership(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> MembershipOut:
    """Returns the candidate's membership state. If they've never started
    checkout, returns a synthetic 'not a member' object (is_active=false)."""
    m = crud_membership.get_by_user_id(db, candidate.user_id)
    if m is None:
        return MembershipOut(user_id=candidate.user_id, is_active=False)
    return MembershipOut.model_validate(m)


@router.post("/portal", response_model=MembershipPortalOut)
def create_portal(
    candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> MembershipPortalOut:
    """Open the Stripe Customer Portal — user manages their own sub there."""
    m = crud_membership.get_by_user_id(db, candidate.user_id)
    if not m or not m.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no Stripe customer yet — start checkout first",
        )
    url = stripe_client.create_portal_session(customer_id=m.stripe_customer_id)
    return MembershipPortalOut(url=url)


# ─────────────────────────────── webhook ──────────────────────────────────


@webhook_router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(default=""),
) -> dict[str, bool]:
    """Receives Stripe events. Signature-verified; no JWT auth.

    Subscribed events (see Stripe Dashboard):
        checkout.session.completed
        customer.subscription.created
        customer.subscription.updated
        customer.subscription.deleted
        invoice.payment_succeeded
        invoice.payment_failed

    Handlers are idempotent — Stripe retries any non-2xx response.
    """
    payload = await request.body()
    try:
        event = stripe_client.construct_event(payload, stripe_signature)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="invalid signature")

    _handle_event(db, event)
    return {"received": True}


def _handle_event(db: Session, event) -> None:
    """Dispatch one Stripe event to the matching membership update."""
    obj = event.data.object
    event_type = event.type

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        crud_membership.update_from_subscription(db, obj)

    elif event_type == "customer.subscription.deleted":
        crud_membership.mark_canceled(db, stripe_subscription_id=obj.id)

    elif event_type in (
        "checkout.session.completed",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
    ):
        # These events carry the subscription ID but not the full object.
        # Fetch the current state and reconcile.
        sub_id = getattr(obj, "subscription", None)
        if sub_id:
            sub = stripe_client.retrieve_subscription(sub_id)
            crud_membership.update_from_subscription(db, sub)

    else:
        log.debug("ignoring stripe event %s", event_type)
