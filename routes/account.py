import zipfile

from flask import redirect, render_template, request, session

from app import app
from db import get_user_by_id, update_user_email
from indieauth_db import create_personal_token, get_personal_token, revoke_personal_token
from routes import require_owner
from substack import import_posts, import_subscribers, rehost_images


def render_account(site, user, **kwargs):
    token = get_personal_token(site["id"])
    return render_template(
        "account.html", site=site, user=user, is_owner=True, personal_token=token, **kwargs
    )


@app.route("/-/account", methods=["GET", "POST"])
def account():
    site = require_owner()
    user = get_user_by_id(session["user_id"])

    if request.method == "GET":
        return render_account(site, user)

    email = request.form.get("email", "").strip().lower()
    if not email:
        return render_account(site, user, error="Email is required.")
    update_user_email(user["id"], email)
    user = get_user_by_id(user["id"])
    return render_account(site, user, success="Email updated.")


@app.route("/-/account/import", methods=["POST"])
def account_import():
    site = require_owner()
    user = get_user_by_id(session["user_id"])

    file = request.files.get("archive")
    if not file:
        return render_account(site, user, import_error="No file selected.")

    try:
        zf = zipfile.ZipFile(file)
    except zipfile.BadZipFile:
        return render_account(site, user, import_error="Invalid zip file.")

    with zf:
        results = import_posts(zf, site["id"])
        results.update(import_subscribers(zf, site["id"]))

    results["images_rehosted"] = rehost_images(site["id"], site["subdomain"])
    return render_account(site, user, import_results=results)


@app.route("/-/account/token", methods=["POST"])
def account_token():
    site = require_owner()
    user = get_user_by_id(session["user_id"])
    token = create_personal_token(site["id"])
    return render_account(site, user, new_token=token)


@app.route("/-/account/token/revoke", methods=["POST"])
def account_token_revoke():
    site = require_owner()
    revoke_personal_token(site["id"])
    return redirect("/-/account")
