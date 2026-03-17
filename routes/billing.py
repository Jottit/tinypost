import os
from datetime import datetime, timezone

import stripe
from flask import abort, jsonify, redirect, render_template, request, session

from app import app
from db import (
    get_user_by_id,
    get_user_by_stripe_customer_id,
    set_user_free,
    set_user_plan,
    update_plan_cancels_at,
    update_plan_expires_at,
)
from routes import require_owner

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

PRICE_IDS = {
    "month": os.environ.get("STRIPE_PRICE_MONTHLY"),
    "year": os.environ.get("STRIPE_PRICE_YEARLY"),
    "lifetime": os.environ.get("STRIPE_PRICE_LIFETIME"),
}


@app.route("/-/settings/subscription")
def settings_subscription():
    site = require_owner()

    portal_url = None
    card_last4 = None
    card_brand = None
    subscription_interval = None
    subscription_amount = None

    plan = site["plan"]
    plan_labels = {"monthly": "Monthly", "yearly": "Yearly", "lifetime": "Lifetime"}
    subscription_interval = plan_labels.get(plan, plan.capitalize())

    if plan == "lifetime":
        subscription_amount = "$150 one-time"
    elif plan != "free" and site.get("stripe_customer_id") and STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
        base = request.host_url.rstrip("/")
        portal = stripe.billing_portal.Session.create(
            customer=site["stripe_customer_id"],
            return_url=f"{base}/-/settings/subscription",
        )
        portal_url = portal.url

        try:
            subs = stripe.Subscription.list(customer=site["stripe_customer_id"], limit=1)
            if subs.data:
                sub = subs.data[0]
                price = sub["items"]["data"][0]["price"]
                amount = price.get("unit_amount", 0) // 100
                interval = price.get("recurring", {}).get("interval", "month")
                subscription_amount = f"${amount} / {interval}"
                pm = sub.get("default_payment_method")
                if pm:
                    pm_obj = stripe.PaymentMethod.retrieve(pm)
                    card = pm_obj.get("card", {})
                    card_last4 = card.get("last4")
                    card_brand = (card.get("brand") or "Card").capitalize()
        except Exception:
            subscription_amount = ""

    return render_template(
        "settings_subscription.html",
        site=site,
        is_owner=True,
        portal_url=portal_url,
        card_last4=card_last4,
        card_brand=card_brand,
        subscription_interval=subscription_interval,
        subscription_amount=subscription_amount,
    )


@app.route("/-/billing/checkout", methods=["POST"])
def billing_checkout():
    user_id = session.get("user_id")
    if not user_id:
        abort(redirect("/signin"))

    interval = request.form.get("interval", "month")
    if interval not in ("month", "year", "lifetime"):
        interval = "month"

    price_id = PRICE_IDS.get(interval)
    if not price_id or not STRIPE_SECRET_KEY:
        abort(500)

    stripe.api_key = STRIPE_SECRET_KEY

    user = get_user_by_id(user_id)
    if not user:
        abort(404)

    base = request.host_url.rstrip("/")
    mode = "payment" if interval == "lifetime" else "subscription"
    checkout_session = stripe.checkout.Session.create(
        customer_email=user["email"] if not user.get("stripe_customer_id") else None,
        customer=user.get("stripe_customer_id") or None,
        mode=mode,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{base}/-/settings/subscription",
        cancel_url=f"{base}/-/settings/subscription",
        metadata={"user_id": str(user["id"]), "plan": interval},
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
        metadata = session_obj.get("metadata", {})
        user_id = metadata.get("user_id")
        customer_id = session_obj.get("customer")
        interval = metadata.get("plan", "monthly")
        plan_map = {"month": "monthly", "year": "yearly", "lifetime": "lifetime"}
        plan = plan_map.get(interval, interval)
        if user_id:
            set_user_plan(int(user_id), plan, customer_id)
            update_plan_cancels_at(int(user_id), None)

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        if customer_id:
            user = get_user_by_stripe_customer_id(customer_id)
            if user:
                cancel_at = subscription.get("cancel_at")
                if subscription.get("cancel_at_period_end") or cancel_at:
                    cancels_at = (
                        datetime.fromtimestamp(cancel_at, tz=timezone.utc) if cancel_at else None
                    )
                    update_plan_cancels_at(user["id"], cancels_at)
                else:
                    update_plan_cancels_at(user["id"], None)

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
