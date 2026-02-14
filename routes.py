from app import app, get_db
from flask import render_template

@app.route("/")
def home():
    return render_template("home.html")
