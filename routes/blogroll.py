from flask import flash, redirect, render_template, request

from app import app
from db import get_blogroll, update_blogroll
from routes import require_owner


@app.route("/blogroll", methods=["GET", "POST"])
def blogroll():
    site = require_owner()

    if request.method == "GET":
        return render_template(
            "blogroll.html", site=site, is_owner=True, blogroll=get_blogroll(site["id"])
        )

    items = []
    i = 0
    while f"blogroll[{i}][name]" in request.form:
        name = request.form.get(f"blogroll[{i}][name]", "").strip()
        url = request.form.get(f"blogroll[{i}][url]", "").strip()
        if name and url:
            items.append({"name": name, "url": url})
        i += 1

    update_blogroll(site["id"], items)
    flash("Blogroll updated.")
    return redirect("/blogroll")
