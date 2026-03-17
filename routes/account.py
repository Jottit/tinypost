from flask import redirect, render_template, request, session

from app import app, limiter
from auth import generate_passcode, hash_passcode, send_passcode, verify_passcode
from db import (
    get_user_by_email,
    update_user_email,
)
from routes import require_owner


@app.route("/-/account")
def account():
    return redirect("/-/account/email")


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
    return redirect("/-/settings")


@app.route("/-/settings/export-import")
def settings_export_import():
    require_owner()
    return redirect("/-/settings/export")
