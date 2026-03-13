from flask import abort, redirect, request, session

from app import app  # noqa: F401 — re-exported for `python app.py` compatibility
from utils import get_current_site, host_and_base


def require_owner():
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        abort(redirect("/signin"))
    return site


@app.after_request
def set_cache_headers(response):
    if request.method != "GET" or response.status_code != 200:
        return response
    host, base = host_and_base()
    if host == base:
        return response
    if request.path.startswith("/-/"):
        return response
    if session.get("user_id"):
        response.headers["Cache-Control"] = "private, no-store"
        return response
    response.headers["Cache-Control"] = "public, max-age=60"
    return response


from routes import (  # noqa: E402, F401
    account,
    auth,
    blogroll,
    errors,
    feeds,
    home,
    indieauth,
    micropub,
    posts,
    settings,
    subscribers,
    uploads,
)
