import os
from datetime import datetime, timezone

import markdown
from flask import Flask
from markupsafe import Markup

from models import close_db

app = Flask(__name__)
app.secret_key = "change-me-later"
app.config["BASE_DOMAIN"] = os.environ.get("BASE_DOMAIN", "jottit.localhost:8000")
app.config["SESSION_COOKIE_DOMAIN"] = app.config["BASE_DOMAIN"].split(":")[0]
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.teardown_appcontext(close_db)


@app.context_processor
def inject_now():
    return {"now": datetime.now(timezone.utc)}


@app.template_filter("markdown")
def markdown_filter(text):
    return Markup(markdown.markdown(text))


@app.template_filter("truncatewords")
def truncatewords_filter(text, n=50):
    words = text.split()
    if len(words) <= n:
        return text
    return " ".join(words[:n]) + "…"


from routes import *

if __name__ == "__main__":
    app.run(debug=True, port=8000)
