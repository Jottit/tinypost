from flask import abort, redirect, session

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
    design,
    feeds,
    home,
    pages,
    posts,
    settings,
    subscribers,
    uploads,
)
