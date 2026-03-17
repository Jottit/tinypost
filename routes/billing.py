import os
from datetime import datetime, timezone

import stripe
from flask import abort, jsonify, redirect, request, session

from app import app
from db import (
    get_user_by_id,
    get_user_by_stripe_customer_id,
    set_user_free,
    set_user_paid,
    update_plan_expires_at,
)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

PRICE_IDS = {
    "month": os.environ.get("STRIPE_PRICE_MONTHLY"),
    "year": os.environ.get("STRIPE_PRICE_YEARLY"),
}


@app.route("/-/billing/checkout", methods=["POST"])
def billing_checkout():
    user_id = session.get("user_id")
    if not user_id:
        abort(redirect("/signin"))

    interval = request.form.get("interval", "month")
    if interval not in ("month", "year"):
        interval = "month"

    price_id = PRICE_IDS.get(interval)
    if not price_id or not STRIPE_SECRET_KEY:
        abort(500)

    stripe.api_key = STRIPE_SECRET_KEY

    user = get_user_by_id(user_id)
    if not user:
        abort(404)

    base = request.host_url.rstrip("/")
    checkout_session = stripe.checkout.Session.create(
        customer_email=user["email"] if not user.get("stripe_customer_id") else None,
        customer=user.get("stripe_customer_id") or None,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{base}/-/settings/domain",
        cancel_url=f"{base}/-/settings/domain",
        metadata={"user_id": str(user["id"])},
    )
    return redirect(checkout_session.url)


@app.route("/-/billing/webhook", methods=["POST"])
def billing_webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature")

    if not STRIPE_WEBHOOK_SECRET or not STRIPE_SECRET_KEY:
        abort(500)

    stripe.api_key = STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        abort(400)

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        user_id = session_obj.get("metadata", {}).get("user_id")
        customer_id = session_obj.get("customer")
        if user_id:
            set_user_paid(int(user_id), customer_id)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        if customer_id:
            user = get_user_by_stripe_customer_id(customer_id)
            if user:
                set_user_free(user["id"])

    elif event["type"] == "invoice.paid":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        period_end = invoice.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
        if customer_id and period_end:
            user = get_user_by_stripe_customer_id(customer_id)
            if user:
                expires_at = datetime.fromtimestamp(period_end, tz=timezone.utc)
                update_plan_expires_at(user["id"], expires_at)

    return jsonify({"status": "ok"})
