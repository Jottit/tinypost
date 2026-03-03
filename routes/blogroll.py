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
    is_owner = session.get("user_id") == site["user_id"]
    items = get_blogroll(site["id"])
    return render_template("blogroll_page.html", site=site, blogroll=items, is_owner=is_owner)


@app.route("/-/blogroll", methods=["GET", "POST"])
def blogroll_edit():
    site = require_owner()

    if request.method == "GET":
        items = get_blogroll(site["id"])
        return render_template("blogroll.html", site=site, is_owner=True, blogroll=items)

    items = []
    i = 0
    while f"blogroll[{i}][name]" in request.form:
        name = request.form.get(f"blogroll[{i}][name]", "").strip()
        url = request.form.get(f"blogroll[{i}][url]", "").strip()
        if name and url:
            items.append({"name": name, "url": url})
        i += 1

    update_blogroll(site["id"], items)
    if request.headers.get("X-Auto-Save"):
        return "", 204
    flash("Blogroll updated.")
    return redirect("/-/blogroll")
