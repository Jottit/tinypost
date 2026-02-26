import secrets

from flask import abort, redirect, render_template, request

from app import app
from db import (
    confirm_subscriber,
    create_subscriber,
    delete_subscriber,
    get_all_subscribers,
    get_site_by_id,
    get_subscriber,
    get_subscriber_by_token,
    unsubscribe,
    update_subscriber_token,
)
from mailer import send_email
from routes import require_owner
from utils import get_current_site, site_url


@app.route("/-/subscribers")
def subscribers():
    site = require_owner()
    subs = get_all_subscribers(site["id"])
    confirmed = sum(1 for s in subs if s["confirmed"])
    pending = len(subs) - confirmed
    return render_template(
        "subscribers.html",
        site=site,
        subscribers=subs,
        total=len(subs),
        confirmed_count=confirmed,
        pending_count=pending,
        is_owner=True,
    )


@app.route("/-/subscribers/delete/<int:subscriber_id>", methods=["POST"])
def subscribers_delete(subscriber_id):
    site = require_owner()
    delete_subscriber(subscriber_id, site["id"])
    return redirect("/-/subscribers")


@app.route("/subscribe", methods=["POST"])
def subscribe():
    site = get_current_site()
    if not site:
        abort(404)

    if request.form.get("website"):
        return render_template("subscribed.html", site=site)

    email = request.form.get("email", "").strip().lower()
    if not email:
        return redirect("/")

    token = secrets.token_urlsafe(32)
    existing = get_subscriber(site["id"], email)
    if existing:
        if existing["confirmed"]:
            return render_template("subscribed.html", site=site)
        update_subscriber_token(existing["id"], token)
    else:
        create_subscriber(site["id"], email, token)

    base_url = site_url(site)
    confirm_url = f"{base_url}/confirm/{token}"
    send_email(
        to=email,
        subject=f"Please confirm your subscription to {site['title']}",
        from_addr=f"Tinypost <confirm-subscriber@{app.config['BASE_DOMAIN']}>",
        text=(
            f"You're almost subscribed to updates from {site['title']}.\n\n"
            f"Confirm your subscription below to get future posts in your inbox.\n\n"
            f"{confirm_url}\n\n"
            f"---\n"
            f"Don't want to subscribe? Feel free to ignore this email."
        ),
        html=render_template(
            "email_confirm_subscription.html",
            site=site,
            confirm_url=confirm_url,
        ),
    )
    return render_template("subscribed.html", site=site)


@app.route("/confirm/<token>")
def confirm(token):
    subscriber = get_subscriber_by_token(token)
    if not subscriber:
        abort(404)
    confirm_subscriber(token)
    site = get_site_by_id(subscriber["site_id"])
    return render_template(
        "confirmed.html",
        site=site,
        token=token,
        base_url=site_url(site),
    )


@app.route("/unsubscribe/<token>")
def unsubscribe_route(token):
    subscriber = get_subscriber_by_token(token)
    if not subscriber:
        abort(404)
    site = get_site_by_id(subscriber["site_id"])
    unsubscribe(token)
    return render_template("unsubscribed.html", site=site, base_url=site_url(site))
