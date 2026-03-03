from flask import redirect, render_template, request, session

from app import app, limiter
from auth import generate_passcode, hash_passcode, send_passcode, verify_passcode
from db import create_user_and_site, get_site_by_user, get_user_by_email
from utils import is_valid_subdomain, subdomain_url


@app.route("/signup", methods=["POST"])
@limiter.limit("5/minute")
def signup_post():
    subdomain = request.form["subdomain"].strip().lower()
    email = request.form["email"].strip().lower()
    if not is_valid_subdomain(subdomain):
        return redirect("/")
    passcode = generate_passcode()
    session["signup"] = {
        "subdomain": subdomain,
        "email": email,
        "passcode": hash_passcode(passcode),
    }
    send_passcode(email, passcode)
    return render_template("signup_verify.html", email=email)


@app.route("/verify", methods=["POST"])
@limiter.limit("10/minute")
def signup_verify():
    signup = session.get("signup")
    if not signup:
        return redirect("/")
    code = request.form["passcode"]
    if not verify_passcode(code, signup["passcode"]):
        return render_template("signup_verify.html", email=signup["email"], error="Wrong passcode.")
    user, site = create_user_and_site(signup["email"], signup["subdomain"])
    session.pop("signup")
    session["user_id"] = user["id"]
    return redirect(subdomain_url(site))


@app.route("/signin")
def signin():
    return render_template("signin.html")


@app.route("/signin", methods=["POST"])
@limiter.limit("5/minute")
def signin_post():
    email = request.form["email"].strip().lower()
    user = get_user_by_email(email)
    if not user:
        return render_template("signin.html", error="No account with that email.")
    passcode = generate_passcode()
    session["signin"] = {"email": email, "user_id": user["id"], "passcode": hash_passcode(passcode)}
    send_passcode(email, passcode)
    return render_template("signin_verify.html", email=email)


@app.route("/signin/verify", methods=["POST"])
@limiter.limit("10/minute")
def signin_verify():
    signin = session.get("signin")
    if not signin:
        return redirect("/signin")
    code = request.form["passcode"]
    if not verify_passcode(code, signin["passcode"]):
        return render_template("signin_verify.html", email=signin["email"], error="Wrong passcode.")
    session.pop("signin")
    session["user_id"] = signin["user_id"]
    site = get_site_by_user(signin["user_id"])
    return redirect(subdomain_url(site))


@app.route("/signout", methods=["POST"])
def signout():
    session.clear()
    return redirect("/")
