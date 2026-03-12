import markdown as md
from flask import abort, jsonify, redirect, render_template, request, session

from app import app
from db import (
    create_post,
    delete_post,
    get_confirmed_subscribers,
    get_post_by_slug,
    get_site_by_user,
    get_subscriber_count,
    get_user_by_id,
    mark_post_sent,
    toggle_post_pinned,
    update_post,
)
from mailer import send_email
from routes import require_owner
from utils import RESERVED_SLUGS, get_current_site, site_url, slugify


@app.route("/-/edit", methods=["GET", "POST"])
def edit():
    site = require_owner()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "GET":
        return render_template("edit.html", site=site)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not body:
        if is_ajax:
            return jsonify(error="Post body is required."), 400
        return render_template("edit.html", site=site, error="Post body is required.")
    slug = slugify(title or body[:50]) or "post"
    if slug in RESERVED_SLUGS:
        if is_ajax:
            return jsonify(error="That URL slug is reserved or already in use."), 400
        return render_template(
            "edit.html", site=site, error="That URL slug is reserved or already in use."
        )
    is_draft = request.form.get("is_draft") == "on"
    create_post(site["id"], slug, title or None, body, is_draft=is_draft)
    if is_ajax:
        return jsonify(slug=slug)
    return redirect(f"/{slug}")


@app.route("/-/edit/<slug>", methods=["GET", "POST"])
def edit_post(slug):
    site = require_owner()
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)

    sub_count = get_subscriber_count(site["id"])

    if request.method == "GET":
        return render_template("edit.html", site=site, post=post, subscriber_count=sub_count)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not body:
        return render_template(
            "edit.html",
            site=site,
            post=post,
            subscriber_count=sub_count,
            error="Post body is required.",
        )
    new_slug = slugify(title or body[:50]) or "post"
    if new_slug in RESERVED_SLUGS:
        return render_template(
            "edit.html",
            site=site,
            post=post,
            subscriber_count=sub_count,
            error="That URL slug is reserved or already in use.",
        )
    is_draft = request.form.get("is_draft") == "on"
    update_post(post["id"], new_slug, title or None, body, is_draft=is_draft)
    return redirect(f"/{new_slug}")


@app.route("/-/delete/<slug>", methods=["POST"])
def delete_post_route(slug):
    site = require_owner()
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    delete_post(post["id"])
    return redirect("/")


@app.route("/-/pin/<slug>", methods=["POST"])
def pin_post(slug):
    site = require_owner()
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    updated = toggle_post_pinned(post["id"])
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(is_pinned=updated["is_pinned"])
    return redirect(f"/{slug}")


@app.route("/-/send/<slug>", methods=["POST"])
def send_post(slug):
    site = require_owner()
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    if post["is_draft"] or post.get("sent_at"):
        return redirect(f"/-/edit/{slug}")

    subscribers = get_confirmed_subscribers(site["id"])
    if not subscribers:
        return redirect(f"/-/edit/{slug}")

    mark_post_sent(post["id"])

    base_url = site_url(site)
    body_html = md.markdown(post["body"])
    post_url = f"{base_url}/{slug}"
    for sub in subscribers:
        unsubscribe_url = f"{base_url}/unsubscribe/{sub['token']}"
        send_email(
            to=sub["email"],
            from_addr=f"Tinypost <noreply@{app.config['BASE_DOMAIN']}>",
            subject=post["title"] or site["title"],
            text=(
                f"{post['title'] or ''}\n\n"
                f"{post['body']}\n\n"
                f"---\n"
                f"You're receiving this because you subscribed to {site['title']}.\n"
                f"Unsubscribe: {unsubscribe_url}"
            ),
            html=render_template(
                "email_post.html",
                site=site,
                post=post,
                body_html=body_html,
                post_url=post_url,
                unsubscribe_url=unsubscribe_url,
            ),
        )

    return redirect(f"/{slug}")


@app.route("/<slug>")
def post(slug):
    site = get_current_site()
    if not site:
        abort(404)
    is_owner = session.get("user_id") == site["user_id"]

    post = get_post_by_slug(site["id"], slug)
    if post:
        if post["is_draft"] and not is_owner:
            abort(404)
        user_id = session.get("user_id")
        user = get_user_by_id(user_id) if user_id else None
        user_site = get_site_by_user(user_id) if user_id else None
        return render_template(
            "post.html",
            site=site,
            post=post,
            is_owner=is_owner,
            subscriber_count=get_subscriber_count(site["id"]) if is_owner else 0,
            user=user,
            user_site=user_site,
        )

    abort(404)
