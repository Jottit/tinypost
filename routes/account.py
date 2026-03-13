from flask import redirect, render_template, request, session

from app import app, limiter
from auth import generate_passcode, hash_passcode, send_passcode, verify_passcode
from db import (
    create_personal_token,
    get_personal_token,
    get_user_by_email,
    get_user_by_id,
    revoke_personal_token,
    update_user,
    update_user_email,
)
from routes import require_owner


def render_account(site, user, **kwargs):
    token = get_personal_token(site["id"])
    return render_template(
        "account.html",
        site=site,
        user=user,
        is_owner=True,
        personal_token=token,
        **kwargs,
    )


@app.route("/-/account", methods=["GET", "POST"])
def account():
    site = require_owner()

    if request.method == "GET":
        return render_account(site, site)

    name = request.form.get("name", "").strip() or None
    update_user(site["id"], name, site["email"])
    if request.headers.get("X-Auto-Save"):
        return "", 204
    user = get_user_by_id(site["id"])
    return render_account(site, user, success="Account updated.")


@app.route("/-/account/email", methods=["GET", "POST"])
@limiter.limit("5/minute", methods=["POST"])
def account_email():
    site = require_owner()

    if request.method == "GET":
        return render_template("account_email.html", site=site)

    email = request.form.get("email", "").strip().lower()
    if not email:
        return render_template("account_email.html", site=site, error="Email is required.")

    if get_user_by_email(email):
        return render_template(
            "account_email.html", site=site, error="That email is already in use."
        )

    passcode = generate_passcode()
    session["email_change"] = {"email": email, "passcode": hash_passcode(passcode)}
    send_passcode(email, passcode)
    return render_template("account_email_verify.html", site=site, email=email)


@app.route("/-/account/email/verify", methods=["POST"])
@limiter.limit("10/minute")
def account_email_verify():
    site = require_owner()

    change = session.get("email_change")
    if not change:
        return redirect("/-/account/email")

    passcode = request.form.get("passcode", "").strip()
    if not verify_passcode(passcode, change["passcode"]):
        return render_template(
            "account_email_verify.html", site=site, email=change["email"], error="Invalid passcode."
        )

    update_user_email(site["id"], change["email"])
    session.pop("email_change", None)
    return redirect("/-/account")


@app.route("/-/settings/export-import")
def settings_export_import():
    require_owner()
    return redirect("/-/settings/export")


@app.route("/-/account/token", methods=["POST"])
def account_token():
    site = require_owner()
    token = create_personal_token(site["id"])
    return render_account(site, site, new_token=token)


@app.route("/-/account/token/revoke", methods=["POST"])
def account_token_revoke():
    site = require_owner()
    revoke_personal_token(site["id"])
    return redirect("/-/account")
