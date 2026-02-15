from flask import abort, redirect, render_template, request, session

from app import app
from auth import generate_passcode, send_passcode
from db import (
    create_post,
    create_user_and_site,
    delete_post,
    get_post_by_slug,
    get_posts_for_site,
    get_site_by_subdomain,
    get_site_by_user,
    get_user_by_email,
    subdomain_taken,
    update_post,
    update_site,
)
from utils import is_valid_subdomain, site_url, slugify


def get_current_site():
    host = request.host.split(":")[0]
    base = app.config["BASE_DOMAIN"].split(":")[0]
    if not host.endswith("." + base):
        return None
    subdomain = host.replace("." + base, "")
    return get_site_by_subdomain(subdomain)


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

    site = get_current_site()
    if not site:
        abort(404)
    posts = get_posts_for_site(site["id"])
    is_owner = session.get("user_id") == site["user_id"]
    return render_template("site.html", site=site, posts=posts, is_owner=is_owner)


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
    return render_template("signin.html")


@app.route("/signin", methods=["POST"])
def signin_post():
    email = request.form["email"].strip().lower()
    user = get_user_by_email(email)
    if not user:
        return render_template("signin.html", error="No account with that email.")
    passcode = generate_passcode()
    session["signin"] = {"email": email, "user_id": user["id"], "passcode": passcode}
    send_passcode(email, passcode)
    return render_template("signin_verify.html", email=email)


@app.route("/signin/verify", methods=["POST"])
def signin_verify():
    signin = session.get("signin")
    if not signin:
        return redirect("/signin")
    code = request.form["passcode"]
    if code != signin["passcode"]:
        return render_template("signin_verify.html", email=signin["email"], error="Wrong passcode.")
    session.pop("signin")
    session["user_id"] = signin["user_id"]
    site = get_site_by_user(signin["user_id"])
    return redirect(site_url(site["subdomain"]))


@app.route("/edit", methods=["GET", "POST"])
def edit():
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        return redirect("/signin")

    if request.method == "GET":
        return render_template("edit.html", site=site)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not body:
        return render_template("edit.html", site=site, error="Post body is required.")
    slug = slugify(title or body[:50]) or "post"
    create_post(site["id"], slug, title or None, body)
    return redirect(f"/{slug}")


@app.route("/edit/<slug>", methods=["GET", "POST"])
def edit_post(slug):
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        return redirect("/signin")
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)

    if request.method == "GET":
        return render_template("edit.html", site=site, post=post)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not body:
        return render_template("edit.html", site=site, post=post, error="Post body is required.")
    new_slug = slugify(title or body[:50]) or "post"
    update_post(post["id"], new_slug, title or None, body)
    return redirect(f"/{new_slug}")


@app.route("/delete/<slug>", methods=["POST"])
def delete_post_route(slug):
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        return redirect("/signin")
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    delete_post(post["id"])
    return redirect("/")


@app.route("/settings", methods=["GET", "POST"])
def settings():
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        return redirect("/signin")

    if request.method == "GET":
        return render_template("settings.html", site=site)

    title = request.form.get("title", "").strip()
    bio = request.form.get("bio", "").strip()
    if not title:
        return render_template("settings.html", site=site, error="Title is required.")
    update_site(site["id"], title, bio or None)
    return redirect("/")


@app.route("/<slug>")
def post(slug):
    site = get_current_site()
    if not site:
        abort(404)
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    is_owner = session.get("user_id") == site["user_id"]
    return render_template("post.html", site=site, post=post, is_owner=is_owner)


@app.route("/signout", methods=["POST"])
def signout():
    session.clear()
    return redirect("/")
