from flask import abort, jsonify, redirect, render_template, request

from app import app
from db import (
    create_page,
    delete_page,
    get_page_by_id,
    get_page_by_slug,
    get_post_by_slug,
    reorder_pages,
    update_page,
)
from routes import require_owner
from utils import slugify


@app.route("/new-page", methods=["GET", "POST"])
def new_page():
    site = require_owner()

    if request.method == "GET":
        title = request.args.get("title", "").strip()
        page = {"title": title, "body": "", "is_draft": False}
        return render_template("edit_page.html", site=site, page=page, new=True)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    slug = slugify(title) if title else None
    page = {"title": title, "body": body, "is_draft": False}

    if not slug:
        return render_template(
            "edit_page.html", site=site, page=page, new=True, error="Title is required."
        )
    if get_post_by_slug(site["id"], slug) or get_page_by_slug(site["id"], slug):
        return render_template(
            "edit_page.html",
            site=site,
            page=page,
            new=True,
            error="That URL slug is already taken.",
        )
    is_draft = request.form.get("is_draft") == "on"
    create_page(site["id"], slug, title, body=body, is_draft=is_draft)
    return redirect(f"/{slug}")


@app.route("/edit-page/<slug>", methods=["GET", "POST"])
def edit_page(slug):
    site = require_owner()
    page = get_page_by_slug(site["id"], slug)
    if not page:
        abort(404)

    if request.method == "GET":
        return render_template("edit_page.html", site=site, page=page)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title:
        return render_template("edit_page.html", site=site, page=page, error="Title is required.")
    is_draft = request.form.get("is_draft") == "on"
    update_page(page["id"], title, body, is_draft=is_draft)
    return redirect(f"/{page['slug']}")


@app.route("/settings/navigation/add", methods=["POST"])
def settings_navigation_add():
    site = require_owner()
    if request.is_json:
        title = (request.get_json().get("title") or "").strip()
    else:
        title = request.form.get("title", "").strip()
    title = title.capitalize()
    slug = slugify(title) if title else None

    error = None
    error_status = 400
    if not slug:
        error = "Title is required."
    elif get_post_by_slug(site["id"], slug) or get_page_by_slug(site["id"], slug):
        error = "That URL slug is already taken."
        error_status = 409

    if error:
        if request.is_json:
            return jsonify({"error": error}), error_status
        from routes.settings import render_settings

        return render_settings(site, nav_error=error)

    create_page(site["id"], slug, title)
    if request.is_json:
        return jsonify({"slug": slug})
    return redirect(f"/edit-page/{slug}")


@app.route("/settings/navigation/delete/<int:page_id>", methods=["POST"])
def settings_navigation_delete(page_id):
    site = require_owner()
    page = get_page_by_id(page_id)
    if not page or page["site_id"] != site["id"]:
        abort(404)
    delete_page(page_id)
    if request.is_json:
        return jsonify({"ok": True})
    return redirect("/")


@app.route("/settings/navigation/reorder", methods=["POST"])
def settings_navigation_reorder():
    site = require_owner()
    data = request.get_json()
    if not data or "order" not in data:
        return jsonify({"error": "Missing order"}), 400
    reorder_pages(site["id"], data["order"])
    return jsonify({"ok": True})
