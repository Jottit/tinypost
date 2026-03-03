import hashlib
from urllib.parse import urlparse

from flask import abort, jsonify, make_response, redirect, render_template, request, session

from app import app, limiter
from auth import generate_passcode, hash_passcode, send_passcode, verify_passcode
from db import (
    create_comment,
    delete_comment,
    get_post_by_slug,
    get_site_by_id,
    get_site_by_user,
    get_user_by_id,
)
from mailer import send_email
from routes import require_owner
from utils import get_current_site, mask_email, site_url


def _hash_email(email):
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def _safe_referrer():
    ref = request.referrer
    if ref:
        parsed = urlparse(ref)
        if not parsed.netloc or parsed.netloc == request.host:
            return ref
    return "/"


@app.route("/-/comment/<slug>", methods=["POST"])
@limiter.limit("10/minute")
def comment_post(slug):
    site = get_current_site()
    if not site:
        abort(404)
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    if not site.get("comments_enabled", False):
        abort(403)

    if request.form.get("website"):
        return jsonify(status="ok")

    body = request.form.get("body", "").strip()
    name = request.form.get("name", "").strip()
    if not body or not name:
        return jsonify(status="error", message="Name and comment are required."), 400
    if len(body) > 5000:
        return jsonify(status="error", message="Comment is too long."), 400
    if len(name) > 100:
        return jsonify(status="error", message="Name is too long."), 400

    user_id = session.get("user_id")
    if user_id:
        user = get_user_by_id(user_id)
        email_hash = _hash_email(user["email"])
        commenter_site = get_site_by_user(user_id)
        author_url = site_url(commenter_site) if commenter_site else None
        comment = create_comment(
            post["id"],
            site["id"],
            name,
            email_hash,
            body,
            user_id=user_id,
            author_url=author_url,
        )
        _notify_owner(site, post, name, body)
        return jsonify(status="ok", comment_id=comment["id"])

    email = request.form.get("email", "").strip().lower()
    if not email:
        return jsonify(status="error", message="Email is required."), 400

    email_hash = _hash_email(email)

    if request.cookies.get("comment_verified") == email_hash:
        comment = create_comment(post["id"], site["id"], name, email_hash, body)
        _notify_owner(site, post, name, body)
        return jsonify(status="ok", comment_id=comment["id"])

    passcode = generate_passcode()
    session["pending_comment"] = {
        "name": name,
        "email": email,
        "email_hash": email_hash,
        "body": body,
        "slug": slug,
        "site_id": site["id"],
        "post_id": post["id"],
        "passcode": hash_passcode(passcode),
    }
    send_passcode(email, passcode)
    return jsonify(status="verify", email=mask_email(email))


@app.route("/-/comment/<slug>/verify", methods=["POST"])
@limiter.limit("10/minute")
def comment_verify(slug):
    pending = session.get("pending_comment")
    if not pending or pending["slug"] != slug:
        return jsonify(status="error", message="No pending comment."), 400

    code = request.form.get("passcode", "").strip()
    if not verify_passcode(code, pending["passcode"]):
        return jsonify(status="error", message="Wrong passcode."), 400

    comment = create_comment(
        pending["post_id"],
        pending["site_id"],
        pending["name"],
        pending["email_hash"],
        pending["body"],
    )
    session.pop("pending_comment")

    site = get_site_by_id(pending["site_id"])
    post = get_post_by_slug(pending["site_id"], slug)
    _notify_owner(site, post, pending["name"], pending["body"])

    resp = make_response(jsonify(status="ok", comment_id=comment["id"]))
    resp.set_cookie(
        "comment_verified",
        pending["email_hash"],
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="Lax",
    )
    return resp


@app.route("/-/comment/<int:comment_id>/delete", methods=["POST"])
def comment_delete(comment_id):
    site = require_owner()
    delete_comment(comment_id, site["id"])
    return redirect(_safe_referrer())


def _notify_owner(site, post, commenter_name, comment_body):
    owner = get_user_by_id(site["user_id"])
    if not owner:
        return
    post_url = f"{site_url(site)}/{post['slug']}"
    send_email(
        to=owner["email"],
        subject=f"New comment on \"{post['title'] or 'your post'}\"",
        text=(
            f"{commenter_name} commented on {post['title'] or 'your post'}:\n\n"
            f"{comment_body}\n\n"
            f"View: {post_url}\n\n"
            f"---\n"
            f"Tinypost"
        ),
        html=render_template(
            "email_comment_notification.html",
            site=site,
            post=post,
            commenter_name=commenter_name,
            comment_body=comment_body,
            post_url=post_url,
        ),
    )
