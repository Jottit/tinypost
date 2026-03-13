from flask import redirect, render_template, request, session

from app import app
from db import get_user_by_custom_domain
from utils import get_current_site

from .home import _user_menu_context


@app.before_request
def redirect_www():
    host = request.host.split(":")[0]
    base = app.config["BASE_DOMAIN"].split(":")[0]
    if host == f"www.{base}":
        return redirect(f"https://{base}{request.full_path}", code=301)
    if host.startswith("www."):
        bare = host[4:]
        if get_user_by_custom_domain(bare):
            return redirect(f"https://{bare}{request.full_path}", code=301)


@app.errorhandler(404)
def page_not_found(e):
    site = get_current_site()
    if site:
        is_owner = session.get("user_id") == site["id"]
        return render_template("404_site.html", site=site, is_owner=is_owner), 404

    return render_template("404.html", **_user_menu_context()), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500
