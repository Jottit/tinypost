import os

import sentry_sdk
from flask import Flask, request
from flask_limiter import Limiter

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

limiter = Limiter(
    lambda: request.headers.get("Fly-Client-IP") or request.remote_addr,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

init_templates(app)
init_cli(app)


from routes import *  # noqa: F401,F403

if __name__ == "__main__":
    app.run(debug=True, port=8000)
