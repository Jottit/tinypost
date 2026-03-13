from flask import abort, jsonify, redirect, render_template, request, session

from app import app
from config import CADDY_ASK_TOKEN
from db import (
    get_blogroll,
    get_posts_for_user,
    get_user_by_custom_domain,
    get_user_by_id,
    get_user_by_subdomain,
    subdomain_taken,
)
from utils import get_current_site, host_and_base, is_valid_subdomain, mask_email, subdomain_url


def _user_menu_context():
    user_id = session.get("user_id")
    user = get_user_by_id(user_id) if user_id else None
    if not user:
        return {"user_email": None, "sites": [], "site": None}
    return {
        "user_email": mask_email(user["email"]),
        "sites": [
            {
                "title": user["title"],
                "url": subdomain_url(user),
                "avatar": user.get("avatar"),
                "address": user.get("custom_domain") or f"{user['subdomain']}.tinypost.blog",
            }
        ],
        "site": user,
    }


@app.route("/healthz")
def healthz():
    return "ok"


@app.route("/", methods=["GET", "POST"])
def home():
    host, base = host_and_base()

    if host == base:
        if request.method == "POST":
            subdomain = request.form.get("subdomain", "").lower().strip()
            if not is_valid_subdomain(subdomain):
                return render_template("home.html", error="Invalid name", subdomain=subdomain)
            if subdomain_taken(subdomain):
                return render_template(
                    "home.html",
                    error=f"{subdomain}.tinypost.blog is not available",
                    subdomain=subdomain,
                )
            return render_template("signup.html", subdomain=subdomain)

        user_id = session.get("user_id")
        if user_id:
            user = get_user_by_id(user_id)
            if user and user.get("subdomain"):
                return redirect(subdomain_url(user))

        return render_template("home.html")

    site = get_current_site()
    if not site:
        abort(404)
    is_owner = session.get("user_id") == site["id"]

    # Redirect unauthenticated subdomain visitors to custom domain
    if (
        not is_owner
        and site.get("custom_domain")
        and site.get("domain_verified_at")
        and host.endswith("." + base)
    ):
        return redirect(f"https://{site['custom_domain']}", code=308)

    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    per_page = 20
    offset = (page - 1) * per_page
    fetched_posts = get_posts_for_user(
        site["id"], include_drafts=is_owner, limit=per_page + 1, offset=offset
    )
    has_next = len(fetched_posts) > per_page
    posts = fetched_posts[:per_page]
    return render_template(
        "site.html",
        site=site,
        posts=posts,
        is_owner=is_owner,
        blogroll=get_blogroll(site["id"]),
        page=page,
        has_next=has_next,
    )


@app.route("/about")
def about():
    host, base = host_and_base()
    if host != base:
        from routes.posts import post

        return post("about")
    return render_template("about.html", **_user_menu_context())


@app.route("/contact")
def contact():
    host, base = host_and_base()
    if host != base:
        from routes.posts import post

        return post("contact")
    return render_template("contact.html", **_user_menu_context())


@app.route("/check-subdomain")
def check_subdomain():
    name = request.args.get("name", "").lower().strip()
    if not is_valid_subdomain(name):
        return jsonify({"error": "Invalid name"})
    if subdomain_taken(name):
        return jsonify({"available": False})
    return jsonify({"available": True})


@app.route("/_tls/ask")
def tls_ask():
    token = request.args.get("token", "")
    domain = request.args.get("domain", "")

    if not CADDY_ASK_TOKEN or token != CADDY_ASK_TOKEN:
        return "", 403

    base = app.config["BASE_DOMAIN"].split(":")[0]

    if domain == base or domain == f"www.{base}":
        return "", 200

    suffix = "." + base
    if domain.endswith(suffix):
        site = get_user_by_subdomain(domain.removesuffix(suffix))
    else:
        site = get_user_by_custom_domain(domain.removeprefix("www."))

    if not site:
        return "", 403

    return "", 200
