import os

import sentry_sdk
from flask import Flask, redirect, request

if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"])

from cli import init_cli
from db import close_db
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
    host = request.host
    base = app.config["BASE_DOMAIN"]
    if host == f"www.{base}" or host == f"www.{base.split(':')[0]}":
        return redirect(f"https://{base}{request.full_path}", code=301)


from indieauth import *
from micropub import *
from routes import *

if __name__ == "__main__":
    app.run(debug=True, port=8000)
