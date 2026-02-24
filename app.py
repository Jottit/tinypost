import os

import sentry_sdk
from flask import Flask, redirect, render_template, request, session

if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"])

from cli import init_cli
from db import close_db, get_pages_for_site, get_site_by_custom_domain
from template_setup import init_templates

app = Flask(__name__)
app.secret_key = "change-me-later"
app.config["BASE_DOMAIN"] = os.environ.get("BASE_DOMAIN", "jottit.localhost:8000")
app.config["SESSION_COOKIE_DOMAIN"] = app.config["BASE_DOMAIN"].split(":")[0]
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.teardown_appcontext(close_db)

init_templates(app)
init_cli(app)


@app.before_request
def redirect_www():
    host = request.host.split(":")[0]
    base = app.config["BASE_DOMAIN"].split(":")[0]
    if host == f"www.{base}":
        return redirect(f"https://{base}{request.full_path}", code=301)
    if host.startswith("www."):
        bare = host[4:]
        if get_site_by_custom_domain(bare):
            return redirect(f"https://{bare}{request.full_path}", code=301)


@app.errorhandler(404)
def page_not_found(e):
    from utils import get_current_site

    site = get_current_site()
    if site:
        is_owner = session.get("user_id") == site["user_id"]
        pages = get_pages_for_site(site["id"], include_drafts=is_owner)
        return render_template("404_site.html", site=site, pages=pages, is_owner=is_owner), 404

    from routes.home import _user_menu_context

    return render_template("404.html", **_user_menu_context()), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


from indieauth import *
from micropub import *
from routes import *

if __name__ == "__main__":
    app.run(debug=True, port=8000)
