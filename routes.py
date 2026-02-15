from flask import redirect, render_template, request, session

from app import app
from auth import generate_passcode, send_passcode
from db import create_user_and_site, get_posts_for_site, get_site_by_subdomain, subdomain_taken
from utils import is_valid_subdomain, site_url


@app.route("/", methods=["GET", "POST"])
def home():
    host = request.host.split(":")[0]
    base = app.config["BASE_DOMAIN"].split(":")[0]

    if host == base:
        if request.method == "POST":
            subdomain = request.form.get("subdomain", "").lower().strip()
            if not is_valid_subdomain(subdomain):
                return render_template("home.html", error="Invalid name")
            if subdomain_taken(subdomain):
                return render_template("home.html", error="Name taken")
            return render_template("signup.html", subdomain=subdomain)
        return render_template("home.html")

    if host.endswith("." + base):
        subdomain = host.replace("." + base, "")
        site = get_site_by_subdomain(subdomain)
        if not site:
            return "Not found", 404
        posts = get_posts_for_site(site["id"])
        return render_template("site.html", site=site, posts=posts)

    return "Not found", 404


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
