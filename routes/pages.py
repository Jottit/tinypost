from flask import abort, redirect, render_template, request

from app import app
from db import (
    create_page,
    delete_page,
    get_page_by_slug,
    get_post_by_slug,
    update_page,
)
from routes import require_owner
from utils import slugify


@app.route("/-/new-page", methods=["GET", "POST"])
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


@app.route("/-/edit-page/<slug>", methods=["GET", "POST"])
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


@app.route("/-/delete-page/<slug>", methods=["POST"])
def delete_page_route(slug):
    site = require_owner()
    page = get_page_by_slug(site["id"], slug)
    if not page:
        abort(404)
    delete_page(page["id"])
    return redirect("/")
