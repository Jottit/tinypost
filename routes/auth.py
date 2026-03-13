from flask import redirect, render_template, request, session

from app import app, limiter
from auth import generate_passcode, hash_passcode, send_passcode, verify_passcode
from db import create_user, get_user_by_email, get_user_by_id, subdomain_taken
from utils import is_valid_subdomain, subdomain_url


@app.route("/signup")
def signup():
    return render_template("signup_name.html")


@app.route("/signup/email", methods=["GET", "POST"])
def signup_email():
    if request.method == "GET":
        name = request.args.get("name", "").strip()
        if not name:
            return redirect("/signup")
        return render_template("signup_email.html", name=name)

    name = request.form.get("name", "").strip()
    if not name:
        return redirect("/signup")
    session["signup"] = {"name": name}
    return render_template("signup_email.html", name=name)


@app.route("/signup/email/send", methods=["POST"])
@limiter.limit("5/minute")
def signup_email_send():
    signup = session.get("signup")
    if not signup or not signup.get("name"):
        return redirect("/signup")

    email = request.form.get("email", "").strip().lower()
    if not email:
        return render_template("signup_email.html", name=signup["name"], error="Email is required.")

    if get_user_by_email(email):
        return render_template(
            "signup_email.html",
            name=signup["name"],
            error="That email is already registered. Try signing in instead.",
        )

    passcode = generate_passcode()
    session["signup"] = {**signup, "email": email, "passcode": hash_passcode(passcode)}
    send_passcode(email, passcode)
    return render_template("signup_verify.html", email=email)


@app.route("/signup/verify", methods=["POST"])
@limiter.limit("10/minute")
def signup_verify():
    signup = session.get("signup")
    if not signup or not signup.get("email"):
        return redirect("/signup")

    code = request.form["passcode"]
    if not verify_passcode(code, signup["passcode"]):
        return render_template("signup_verify.html", email=signup["email"], error="Wrong passcode.")

    session["signup"] = {**signup, "verified": True}
    return render_template("signup_address.html")


@app.route("/signup/address", methods=["POST"])
def signup_address():
    signup = session.get("signup")
    if not signup or not signup.get("verified"):
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
    from db import update_user

    update_user(user["id"], signup["name"], signup["email"])
    session.pop("signup")
    session["user_id"] = user["id"]
    return redirect(subdomain_url(user))


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
    user = get_user_by_id(signin["user_id"])
    return redirect(subdomain_url(user))


@app.route("/signout", methods=["POST"])
def signout():
    session.clear()
    return redirect("/")
