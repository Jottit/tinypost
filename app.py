import os

import sentry_sdk
from flask import Flask, request, session

if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"])

from cli import init_cli
from db import close_db
from template_setup import init_templates

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["BASE_DOMAIN"] = os.environ.get("BASE_DOMAIN", "tinypost.localhost:8000")
app.config["SESSION_COOKIE_DOMAIN"] = app.config["BASE_DOMAIN"].split(":")[0]
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.teardown_appcontext(close_db)

init_templates(app)
init_cli(app)


from routes import *  # noqa: F401,F403


@app.after_request
def set_cache_headers(response):
    if request.method != "GET" or response.status_code != 200:
        return response
    from utils import host_and_base

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


if __name__ == "__main__":
    app.run(debug=True, port=8000)
