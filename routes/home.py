from flask import abort, jsonify, redirect, render_template, request, session

from app import app
from config import CADDY_ASK_TOKEN
from db import (
    get_blogroll,
    get_pages_for_site,
    get_posts_for_site,
    get_site_by_custom_domain,
    get_site_by_subdomain,
    get_site_by_user,
    get_subscriber_count,
    get_user_by_id,
    subdomain_taken,
)
from utils import get_current_site, host_and_base, is_valid_subdomain, mask_email, subdomain_url


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
                    error=f"{subdomain}.jottit.pub is not available",
                    subdomain=subdomain,
                )
            return render_template("signup.html", subdomain=subdomain)

        user_id = session.get("user_id")
        user = get_user_by_id(user_id) if user_id else None
        site = get_site_by_user(user_id) if user else None
        return render_template(
            "home.html",
            user_email=mask_email(user["email"]) if user and site else None,
            user_site_url=subdomain_url(site) if user and site else None,
        )

    site = get_current_site()
    if not site:
        abort(404)
    is_owner = session.get("user_id") == site["user_id"]

    # Redirect unauthenticated subdomain visitors to custom domain
    if (
        not is_owner
        and site.get("custom_domain")
        and site.get("domain_verified_at")
        and host.endswith("." + base)
    ):
        return redirect(f"https://{site['custom_domain']}", code=308)

    posts = get_posts_for_site(site["id"], include_drafts=is_owner)
    pages = get_pages_for_site(site["id"], include_drafts=is_owner)
    return render_template(
        "site.html",
        site=site,
        posts=posts,
        pages=pages,
        is_owner=is_owner,
        subscriber_count=get_subscriber_count(site["id"]) if is_owner else 0,
        blogroll=get_blogroll(site["id"]),
    )


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
    suffix = "." + base
    if domain.endswith(suffix):
        site = get_site_by_subdomain(domain.removesuffix(suffix))
    else:
        site = get_site_by_custom_domain(domain)

    if not site:
        return "", 403

    return "", 200
