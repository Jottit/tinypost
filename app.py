from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/<path:path>")
def catch_all(path):
    return render_template("gone.html", path=path), 410
