from flask import abort, flash, redirect, render_template, request, session

from app import app
from db import get_blogroll, update_blogroll
from routes import require_owner
from utils import get_current_site


@app.route("/blogroll")
def blogroll():
    site = get_current_site()
    if not site:
        abort(404)
    is_owner = session.get("user_id") == site["id"]
    items = get_blogroll(site["id"])
    return render_template(
        "blogroll_page.html", site=site, blogroll=items, is_owner=is_owner, owner=site
    )


@app.route("/-/blogroll")
def blogroll_edit_redirect():
    return redirect("/-/following", code=301)


@app.route("/-/following")
def following():
    site = require_owner()
    items = get_blogroll(site["id"])
    return render_template("blogroll.html", site=site, is_owner=True, blogroll=items)


@app.route("/-/following/add", methods=["POST"])
def following_add():
    site = require_owner()
    url = request.form.get("url", "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    if url:
        items = get_blogroll(site["id"])
        existing_urls = {item["url"] for item in items}
        if url not in existing_urls:
            new_items = [{"name": item["name"], "url": item["url"]} for item in items]
            new_items.append({"name": url, "url": url})
            update_blogroll(site["id"], new_items)
            flash("Following updated.")
    return redirect("/-/following")


@app.route("/-/following/remove", methods=["POST"])
def following_remove():
    site = require_owner()
    url = request.form.get("url", "").strip()
    if url:
        items = get_blogroll(site["id"])
        new_items = [
            {"name": item["name"], "url": item["url"]} for item in items if item["url"] != url
        ]
        update_blogroll(site["id"], new_items)
        flash("Following updated.")
    return redirect("/-/following")
