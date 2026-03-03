import io
import secrets
import zipfile

import dns.resolver
from flask import Response, flash, redirect, render_template, request, session

from app import app
from config import ALLOWED_IMAGE_TYPES, CUSTOM_DOMAIN_IPV4, CUSTOM_DOMAIN_IPV6
from db import (
    delete_account,
    delete_site,
    get_all_posts_for_site,
    get_pages_for_site,
    get_sites_by_user,
    is_domain_taken,
    remove_custom_domain,
    set_custom_domain,
    update_site,
    update_site_avatar,
    verify_custom_domain,
)
from routes import require_owner
from storage import (
    crop_square,
    delete_all_images,
    delete_image,
    download_image,
    list_images,
    upload_image,
    validate_image,
)


def render_settings(site, **kwargs):
    return render_template(
        "settings.html",
        site=site,
        is_owner=True,
        custom_domain_ipv4=CUSTOM_DOMAIN_IPV4,
        custom_domain_ipv6=CUSTOM_DOMAIN_IPV6,
        **kwargs,
    )


@app.route("/-/settings", methods=["GET", "POST"])
def settings():
    site = require_owner()

    if request.method == "GET":
        return render_settings(site)

    title = request.form.get("title", "").strip()
    bio = request.form.get("bio", "").strip()
    license = request.form.get("license", "").strip() or None
    if not title:
        return render_settings(site, error="Title is required.")

    social_links = []
    i = 0
    while f"social_links[{i}][label]" in request.form:
        label = request.form.get(f"social_links[{i}][label]", "").strip()
        url = request.form.get(f"social_links[{i}][url]", "").strip()
        if label and url:
            social_links.append({"label": label, "url": url})
        i += 1

    comments_enabled = request.form.get("comments_enabled") == "on"
    menu = request.form.get("menu", "").strip() or None
    update_site(
        site["id"],
        title,
        bio or None,
        license=license,
        social_links=social_links,
        comments_enabled=comments_enabled,
        menu=menu,
    )
    flash("Settings updated.")
    return redirect("/-/settings")


@app.route("/-/settings/avatar", methods=["POST"])
def settings_avatar():
    site = require_owner()

    file = request.files.get("avatar")
    if not file:
        return redirect("/-/settings")

    error = validate_image(file)
    if error:
        return render_settings(site, error=f"{error}.")

    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    fmt = file.content_type.split("/")[-1].upper()
    cropped = crop_square(file, fmt)
    key = f"{site['subdomain']}/avatar.{ext}"
    url = upload_image(key, cropped, file.content_type)
    update_site_avatar(site["id"], url)
    return redirect("/-/settings")


@app.route("/-/settings/avatar/delete", methods=["POST"])
def settings_avatar_delete():
    site = require_owner()

    if site["avatar"]:
        url = site["avatar"]
        if url.startswith("/uploads/"):
            key = url.removeprefix("/uploads/")
        else:
            key = "/".join(url.split("/")[3:])
        if key:
            delete_image(key)
        update_site_avatar(site["id"], None)
    return redirect("/-/settings")


@app.route("/-/settings/export")
def settings_export():
    site = require_owner()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in get_all_posts_for_site(site["id"]):
            content = f"# {p['title']}\n\n{p['body']}" if p["title"] else p["body"]
            folder = "drafts/" if p["is_draft"] else ""
            zf.writestr(f"{folder}{p['slug']}.md", content)

        for p in get_pages_for_site(site["id"], include_drafts=True):
            content = f"# {p['title']}\n\n{p['body']}" if p["body"] else f"# {p['title']}"
            zf.writestr(f"pages/{p['slug']}.md", content)

        for key in list_images(site["subdomain"]):
            data = download_image(key)
            if data:
                filename = key.split("/", 1)[1]
                zf.writestr(f"images/{filename}", data)

    return Response(
        buf.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{site["subdomain"]}-export.zip"'},
    )


@app.route("/-/settings/domain", methods=["POST"])
def settings_domain():
    site = require_owner()
    domain = request.form.get("domain", "").strip().lower()

    if not domain or "." not in domain or " " in domain or "://" in domain:
        return render_settings(site, domain_error="Enter a valid domain name.")

    if is_domain_taken(domain, exclude_site_id=site["id"]):
        return render_settings(site, domain_error="That domain is already in use.")

    token = secrets.token_urlsafe(24)
    set_custom_domain(site["id"], domain, token)
    return redirect("/-/settings")


@app.route("/-/settings/domain/verify", methods=["POST"])
def settings_domain_verify():
    site = require_owner()

    if not site.get("custom_domain") or not site.get("domain_verification_token"):
        return redirect("/-/settings")

    domain = site["custom_domain"]
    token = site["domain_verification_token"]

    try:
        answers = dns.resolver.resolve(f"_tinypost.{domain}", "TXT")
        found = any(f"tinypost-site-verification={token}" in str(r) for r in answers)
    except Exception:
        found = False

    if not found:
        return render_settings(
            site, domain_error="TXT record not found. It may take a few minutes to propagate."
        )

    verify_custom_domain(site["id"])
    return redirect("/-/settings")


@app.route("/-/settings/domain/remove", methods=["POST"])
def settings_domain_remove():
    site = require_owner()
    remove_custom_domain(site["id"])
    return redirect("/-/settings")


@app.route("/-/settings/delete-site", methods=["GET", "POST"])
def settings_delete_site():
    site = require_owner()

    if request.method == "GET":
        return render_template("delete_site.html", site=site, is_owner=True)

    if request.form.get("confirmation") != "delete":
        return render_template(
            "delete_site.html", site=site, is_owner=True, error="Type 'delete' to confirm."
        )

    delete_all_images(site["subdomain"])
    user_id = session["user_id"]
    delete_site(site["id"])

    remaining = get_sites_by_user(user_id)
    if not remaining:
        delete_account(user_id)
        session.clear()

    return redirect(f"http://{app.config['BASE_DOMAIN']}")


@app.route("/-/settings/delete-account", methods=["GET", "POST"])
def settings_delete_account():
    site = require_owner()
    sites = get_sites_by_user(session["user_id"])

    if request.method == "GET":
        return render_template("delete_account.html", site=site, sites=sites, is_owner=True)

    if request.form.get("confirmation") != "delete":
        return render_template(
            "delete_account.html",
            site=site,
            sites=sites,
            is_owner=True,
            error="Type 'delete' to confirm.",
        )

    for s in sites:
        delete_all_images(s["subdomain"])
    delete_account(session["user_id"])
    session.clear()
    return redirect(f"http://{app.config['BASE_DOMAIN']}")
