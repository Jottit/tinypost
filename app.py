import os
from flask import Flask
from models import close_db

app = Flask(__name__)
app.secret_key = "change-me-later"
app.config["BASE_DOMAIN"] = os.environ.get("BASE_DOMAIN", "jottit.localhost:8000")
app.teardown_appcontext(close_db)

from routes import *

if __name__ == "__main__":
    app.run(debug=True, port=8000)
