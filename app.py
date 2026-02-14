from flask import Flask, g, render_template
import psycopg

app = Flask(__name__)
app.secret_key = "change-me-later"

def get_db():
    if "db" not in g:
        dbname = app.config.get("DATABASE", "jottit")
        g.db = psycopg.connect(f"dbname={dbname}")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

from routes import *

if __name__ == "__main__":
    app.run(debug=True, port=5001)
