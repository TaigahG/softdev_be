from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Membership


_ACTIVE_STATUSES = {"active", "trialing"}


def get_by_user_id(db: Session, user_id: UUID) -> Optional[Membership]:
    return (
        db.query(Membership).filter(Membership.user_id == user_id).first()
    )


def get_by_customer_id(
    db: Session, stripe_customer_id: str
) -> Optional[Membership]:
    return (
        db.query(Membership)
        .filter(Membership.stripe_customer_id == stripe_customer_id)
        .first()
    )


def get_by_subscription_id(
    db: Session, stripe_subscription_id: str
) -> Optional[Membership]:
    return (
        db.query(Membership)
        .filter(Membership.stripe_subscription_id == stripe_subscription_id)
        .first()
    )


def upsert_customer(
    db: Session, *, user_id: UUID, stripe_customer_id: str
) -> Membership:
    """Called at first checkout attempt — guarantee a Membership row exists with
    this customer_id, so the webhook can find it by customer when payment lands."""
    m = get_by_user_id(db, user_id)
    if m is None:
        m = Membership(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            is_active=False,
        )
        db.add(m)
    else:
        m.stripe_customer_id = stripe_customer_id
    db.commit()
    db.refresh(m)
    return m


def _ts_to_date(ts: Optional[int]):
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).date()


def _period_dates_from_subscription(subscription: Any) -> tuple:
    """Newer Stripe API versions (≥ 2026-02-25) moved current_period_start /
    current_period_end off the subscription onto each subscription item. For a
    single-item subscription (our case — one membership Price), read from the
    first item. Older subs still expose them top-level; fall back to that."""
    # Note: subscription.items is shadowed by dict.items() — use [] access.
    try:
        item = subscription["items"].data[0]
    except (KeyError, IndexError, AttributeError, TypeError):
        item = None

    start = None
    end = None
    if item is not None:
        start = item.get("current_period_start") if hasattr(item, "get") else None
        end = item.get("current_period_end") if hasattr(item, "get") else None
    if start is None:
        start = subscription.get("current_period_start") if hasattr(subscription, "get") else None
    if end is None:
        end = subscription.get("current_period_end") if hasattr(subscription, "get") else None
    return start, end


def update_from_subscription(
    db: Session, subscription: Any
) -> Optional[Membership]:
    """Apply a Stripe subscription object to our row. Idempotent.

    Resolves the row by stripe_subscription_id first (most accurate), falling
    back to stripe_customer_id (the row created at checkout time before the
    sub existed).
    """
    sub_id = subscription.id
    customer_id = subscription.customer

    m = get_by_subscription_id(db, sub_id) or get_by_customer_id(
        db, customer_id
    )
    if m is None:
        # No matching row — webhook arrived before we knew about this customer.
        # Could happen for subs created directly in Stripe Dashboard. Skip.
        return None

    period_start, period_end = _period_dates_from_subscription(subscription)
    m.stripe_subscription_id = sub_id
    m.stripe_customer_id = customer_id
    m.status = subscription.status
    m.cancel_at_period_end = bool(subscription.cancel_at_period_end)
    m.start_date = _ts_to_date(period_start)
    m.end_date = _ts_to_date(period_end)
    m.is_active = subscription.status in _ACTIVE_STATUSES

    db.commit()
    db.refresh(m)
    return m


def mark_canceled(
    db: Session, *, stripe_subscription_id: str
) -> Optional[Membership]:
    """Hard-cancel handler for customer.subscription.deleted."""
    m = get_by_subscription_id(db, stripe_subscription_id)
    if m is None:
        return None
    m.is_active = False
    m.status = "canceled"
    m.cancel_at_period_end = False
    db.commit()
    db.refresh(m)
    return m


def is_active_member(db: Session, user_id: UUID) -> bool:
    """Helper used by future recommendations endpoint to gate the cap."""
    m = get_by_user_id(db, user_id)
    return bool(m and m.is_active)
