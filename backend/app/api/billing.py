"""Stripe billing endpoints.

Handles checkout session creation and webhook processing for subscription
lifecycle events. Free tier = public streamers. Pro = personalized recs +
league import + 9-cat.
"""
from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User
from .google_auth import get_current_user, require_user

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str = "monthly"  # monthly | season


@router.post("/checkout")
def create_checkout(req: CheckoutRequest, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    """Create a Stripe Checkout session for Pro subscription."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    stripe.api_key = settings.stripe_secret_key

    if user.tier == "pro":
        raise HTTPException(status_code=400, detail="Already on Pro.")

    price_id = (
        settings.stripe_pro_season_price_id if req.plan == "season"
        else settings.stripe_pro_monthly_price_id
    )
    if not price_id:
        raise HTTPException(status_code=503, detail=f"No Stripe price configured for plan '{req.plan}'.")

    if user.stripe_customer_id:
        customer_id = user.stripe_customer_id
    else:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
        user.stripe_customer_id = customer.id
        db.commit()
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/billing/cancel",
        metadata={"user_id": str(user.id)},
    )
    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/status")
def billing_status(user: User = Depends(require_user)) -> dict:
    """Return the current billing status for the authenticated user."""
    return {"user_id": user.id, "tier": user.tier, "has_subscription": bool(user.stripe_subscription_id)}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events for subscription lifecycle."""
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhooks not configured.")

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}") from e

    obj = event.data.object

    if event.type == "checkout.session.completed":
        user_id = int(obj.metadata.get("user_id", 0))
        sub_id = obj.subscription
        if user_id and sub_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.tier = "pro"
                user.stripe_subscription_id = sub_id
                db.commit()

    elif event.type in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub_id = obj.id
        user = db.query(User).filter(User.stripe_subscription_id == sub_id).first()
        if user:
            user.tier = "pro" if obj.status in ("active", "trialing") else "free"
            if user.tier == "free":
                user.stripe_subscription_id = None
            db.commit()

    return {"received": True}
