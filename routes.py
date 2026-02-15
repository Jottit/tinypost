from app import app
from flask import render_template, request, redirect, session
from utils import is_valid_subdomain, site_url
from auth import generate_passcode, send_passcode
from db import subdomain_taken, create_user_and_site

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        subdomain = request.form.get("subdomain", "").lower().strip()
        if not is_valid_subdomain(subdomain):
            return render_template("home.html", error="Invalid name")

        if subdomain_taken(subdomain):
            return render_template("home.html", error="Name taken")

        return render_template("signup.html", subdomain=subdomain)

    return render_template("home.html")

@app.route("/signup", methods=["POST"])
def signup_post():
    subdomain = request.form["subdomain"]
    email = request.form["email"].strip().lower()
    passcode = generate_passcode()
    session["signup"] = {"subdomain": subdomain, "email": email, "passcode": passcode}
    send_passcode(email, passcode)
    return render_template("signup_verify.html", email=email)

@app.route("/verify", methods=["POST"])
def signup_verify():
    signup = session.get("signup")
    if not signup:
        return redirect("/")
    code = request.form["passcode"]
    if code != signup["passcode"]:
        return render_template("signup_verify.html", email=signup["email"], error="Wrong passcode.")
    user, site = create_user_and_site(signup["email"], signup["subdomain"])
    session.pop("signup")
    session["user_id"] = user["id"]
    return redirect(site_url(signup["subdomain"]))

@app.route("/signin")
def signin():
    # TODO
    return None

@app.route("/signin", methods=["POST"])
def signin_post():
    # TODO
    return None

@app.route("/signout", methods=["POST"])
def signout():
    # TODO
    return None
