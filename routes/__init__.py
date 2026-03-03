from flask import abort, redirect, session

from app import app  # noqa: F401 — re-exported for `python app.py` compatibility
from utils import get_current_site


def require_owner():
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        abort(redirect("/signin"))
    return site


from routes import (  # noqa: E402, F401
    account,
    auth,
    blogroll,
    comments,
    design,
    errors,
    feeds,
    home,
    indieauth,
    micropub,
    pages,
    posts,
    settings,
    subscribers,
    uploads,
)
