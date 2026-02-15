import os

import markdown
from flask import Flask
from markupsafe import Markup

from models import close_db

app = Flask(__name__)
app.secret_key = "change-me-later"
app.config["BASE_DOMAIN"] = os.environ.get("BASE_DOMAIN", "jottit.localhost:8000")
app.teardown_appcontext(close_db)


@app.template_filter("markdown")
def markdown_filter(text):
    return Markup(markdown.markdown(text))

from routes import *

if __name__ == "__main__":
    app.run(debug=True, port=8000)
