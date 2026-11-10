import re

from flask import redirect, render_template, request, session

from app import app, limiter
from auth import check_passcode, issue_passcode, send_passcode
from db import create_user, get_user_by_email, subdomain_taken
from utils import is_valid_subdomain, subdomain_url


def _slugify_name(name):
    first = name.split()[0] if name.split() else name
    slug = re.sub(r"[^a-z0-9]", "", first.lower())[:32]
    if not slug:
        return ""
    if not subdomain_taken(slug):
        return slug
    for i in range(2, 100):
        candidate = f"{slug[:29]}{i}"
        if not subdomain_taken(candidate):
            return candidate
    return slug


@app.route("/signup")
def signup():
    return render_template("signup_email.html")


@app.route("/signup/email/send", methods=["POST"])
@limiter.limit("5/minute")
def signup_email_send():
    email = request.form.get("email", "").strip().lower()
    if not email:
        return render_template("signup_email.html", error="Email is required.")

    if get_user_by_email(email):
        return render_template(
            "signup_email.html",
            error="That email is already registered. Try signing in instead.",
        )

    passcode = issue_passcode(email, "signup")
    session["signup"] = {"email": email}
    send_passcode(email, passcode)
    return render_template("signup_verify.html", email=email)


@app.route("/signup/verify", methods=["POST"])
@limiter.limit("10/minute")
def signup_verify():
    signup = session.get("signup")
    if not signup or not signup.get("email"):
        return redirect("/signup")

    code = request.form["passcode"]
    if not check_passcode(signup["email"], "signup", code):
        return render_template("signup_verify.html", email=signup["email"], error="Wrong passcode.")

    session["signup"] = {**signup, "verified": True}
    return render_template("signup_name.html")


@app.route("/signup/name", methods=["POST"])
def signup_name():
    signup = session.get("signup")
    if not signup or not signup.get("verified"):
        return redirect("/signup")

    name = request.form.get("name", "").strip()
    if not name:
        return render_template("signup_name.html", error="Name is required.")

    session["signup"] = {**signup, "name": name}
    suggested = _slugify_name(name)
    return render_template("signup_address.html", suggested=suggested)


@app.route("/signup/address", methods=["POST"])
def signup_address():
    signup = session.get("signup")
    if not signup or not signup.get("name"):
        return redirect("/signup")

    subdomain = request.form.get("subdomain", "").strip().lower()
    if not is_valid_subdomain(subdomain):
        return render_template(
            "signup_address.html",
            error="Must be 1-32 characters: lowercase letters, numbers, and hyphens.",
        )
    if subdomain_taken(subdomain):
        return render_template(
            "signup_address.html",
            error=f"{subdomain}.tinypost.blog is not available.",
        )

    user = create_user(signup["email"], subdomain)
    from db import update_user, update_user_blog

    update_user(user["id"], signup["name"], signup["email"])
    update_user_blog(user["id"], signup["name"], None)
    session.pop("signup")
    session["user_id"] = user["id"]
    return redirect(subdomain_url(user, path="/-/welcome/photo"))


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
    passcode = issue_passcode(email, "signin", user["id"])
    session["signin"] = {"email": email}
    send_passcode(email, passcode)
    return render_template("signin_verify.html", email=email)


@app.route("/signin/verify", methods=["POST"])
@limiter.limit("10/minute")
def signin_verify():
    signin = session.get("signin")
    if not signin:
        return redirect("/signin")
    user = get_user_by_email(signin["email"])
    if not user:
        session.pop("signin")
        return redirect("/signin")
    code = request.form["passcode"]
    if not check_passcode(signin["email"], "signin", code, user["id"]):
        return render_template("signin_verify.html", email=signin["email"], error="Wrong passcode.")
    session.pop("signin")
    session["user_id"] = user["id"]
    return redirect(subdomain_url(user))


@app.route("/signout", methods=["POST"])
def signout():
    session.clear()
    return redirect(f"http://{app.config['BASE_DOMAIN']}")
