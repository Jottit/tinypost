import hmac
import secrets

from flask import abort, request, session

from utils import host_and_base

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Endpoints authenticated by something other than the session cookie.
EXEMPT_PATHS = {"/micropub", "/micropub/media", "/auth/token", "/-/billing/webhook"}


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def on_session_cookie_domain():
    host, base = host_and_base()
    return host == base or host.endswith("." + base)


def check_csrf():
    if request.method not in UNSAFE_METHODS or request.path in EXEMPT_PATHS:
        return
    # Custom domains never receive the session cookie, so there is no session to forge.
    if not on_session_cookie_domain():
        return
    expected = session.get("csrf_token", "")
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected.encode(), sent.encode()):
        abort(400)


def init_csrf(app):
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.before_request(check_csrf)
