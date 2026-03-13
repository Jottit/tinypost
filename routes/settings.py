import io
import secrets
import zipfile

import dns.resolver
from flask import Response, flash, redirect, render_template, request, session

from app import app
from appearance import APPEARANCE_PRESETS, DEFAULT_APPEARANCE, get_appearance_preset
from config import ALLOWED_IMAGE_TYPES, CUSTOM_DOMAIN_IPV4, CUSTOM_DOMAIN_IPV6
from db import (
    delete_account,
    get_all_posts_for_user,
    get_user_by_id,
    is_domain_taken,
    remove_custom_domain,
    set_custom_domain,
    subdomain_taken,
    update_user_avatar,
    update_user_blog,
    update_user_license,
    update_user_links,
    update_user_subdomain,
    update_user_theme,
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
from utils import is_valid_subdomain

LICENSE_LABELS = {
    "all-rights-reserved": "\u00a9 All Rights Reserved",
    "cc-by-4.0": "CC BY 4.0",
    "cc-by-sa-4.0": "CC BY-SA 4.0",
    "cc-by-nc-4.0": "CC BY-NC 4.0",
    "cc-by-nc-sa-4.0": "CC BY-NC-SA 4.0",
    "cc0-1.0": "CC0 (Public Domain)",
}


@app.route("/-/settings")
def settings():
    site = require_owner()
    return render_template(
        "settings.html",
        site=site,
        user=site,
        is_owner=True,
        license_label=LICENSE_LABELS.get(site.get("license"), ""),
    )


@app.route("/-/settings/blog", methods=["GET", "POST"])
def settings_blog():
    site = require_owner()

    if request.method == "GET":
        return render_template("settings_blog.html", site=site, is_owner=True)

    title = request.form.get("title", "").strip()
    bio = request.form.get("bio", "").strip()
    license = request.form.get("license", "").strip() or None
    if not title:
        return render_template(
            "settings_blog.html", site=site, is_owner=True, error="Title is required."
        )

    update_user_blog(site["id"], title, bio or None, license)
    if request.headers.get("X-Auto-Save"):
        return "", 204
    flash("Blog profile updated.")
    return redirect("/-/settings")


@app.route("/-/settings/subdomain", methods=["GET", "POST"])
def settings_subdomain():
    site = require_owner()

    if request.method == "GET":
        return render_template("settings_subdomain.html", site=site, is_owner=True)

    subdomain = request.form.get("subdomain", "").strip().lower()
    if not is_valid_subdomain(subdomain):
        return render_template(
            "settings_subdomain.html",
            site=site,
            is_owner=True,
            error="Subdomain must be 1-32 characters, lowercase letters, numbers, and hyphens.",
        )

    if subdomain != site["subdomain"] and subdomain_taken(subdomain):
        return render_template(
            "settings_subdomain.html",
            site=site,
            is_owner=True,
            error="That subdomain is already taken.",
        )

    if subdomain != site["subdomain"]:
        update_user_subdomain(site["id"], subdomain)
        if request.headers.get("X-Auto-Save"):
            return "", 204
        flash("Subdomain updated.")
        new_base = f"http://{subdomain}.{app.config['BASE_DOMAIN']}"
        return redirect(f"{new_base}/-/settings")
    if request.headers.get("X-Auto-Save"):
        return "", 204
    return redirect("/-/settings/subdomain")


@app.route("/-/settings/social", methods=["GET", "POST"])
def settings_social():
    site = require_owner()

    if request.method == "GET":
        return render_template("settings_social.html", site=site, is_owner=True)

    links = []
    i = 0
    while f"social_links[{i}][label]" in request.form:
        label = request.form.get(f"social_links[{i}][label]", "").strip()
        url = request.form.get(f"social_links[{i}][url]", "").strip()
        if label and url:
            links.append({"label": label, "url": url})
        i += 1

    update_user_links(site["id"], links)
    if request.headers.get("X-Auto-Save"):
        return "", 204
    flash("Links updated.")
    return redirect("/-/settings")


@app.route("/-/settings/theme", methods=["GET", "POST"])
def settings_appearance():
    site = require_owner()
    current_preset = get_appearance_preset(site)

    if request.method == "GET":
        return render_template(
            "settings_appearance.html",
            site=site,
            is_owner=True,
            presets=APPEARANCE_PRESETS,
            current_preset=current_preset,
        )

    preset = request.form.get("preset", "").strip()
    if preset not in APPEARANCE_PRESETS:
        preset = DEFAULT_APPEARANCE

    update_user_theme(site["id"], preset)
    if request.headers.get("X-Auto-Save"):
        return "", 204
    flash("Theme updated.")
    return redirect("/-/settings")


@app.route("/-/settings/license", methods=["GET", "POST"])
def settings_license():
    site = require_owner()

    if request.method == "GET":
        return render_template("settings_license.html", site=site, is_owner=True)

    license = request.form.get("license", "").strip() or None
    update_user_license(site["id"], license)
    if request.headers.get("X-Auto-Save"):
        return "", 204
    flash("License updated.")
    return redirect("/-/settings")


@app.route("/-/settings/avatar", methods=["POST"])
def settings_avatar():
    site = require_owner()

    file = request.files.get("avatar")
    if not file:
        return redirect("/-/settings/blog")

    error = validate_image(file)
    if error:
        return render_template("settings_blog.html", site=site, is_owner=True, error=f"{error}.")

    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    fmt = file.content_type.split("/")[-1].upper()
    cropped = crop_square(file, fmt)
    key = f"{site['subdomain']}/avatar.{ext}"
    url = upload_image(key, cropped, file.content_type)
    update_user_avatar(site["id"], url)
    return redirect("/-/settings/blog")


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
        update_user_avatar(site["id"], None)
    return redirect("/-/settings/blog")


@app.route("/-/settings/export")
def settings_export():
    site = require_owner()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in get_all_posts_for_user(site["id"]):
            content = f"# {p['title']}\n\n{p['body']}" if p["title"] else p["body"]
            folder = "drafts/" if p["is_draft"] else ""
            zf.writestr(f"{folder}{p['slug']}.md", content)

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


def render_domain(site, **kwargs):
    return render_template(
        "settings_domain.html",
        site=site,
        is_owner=True,
        custom_domain_ipv4=CUSTOM_DOMAIN_IPV4,
        custom_domain_ipv6=CUSTOM_DOMAIN_IPV6,
        **kwargs,
    )


@app.route("/-/settings/domain", methods=["GET", "POST"])
def settings_domain():
    site = require_owner()

    if request.method == "GET":
        return render_domain(site)

    domain = request.form.get("domain", "").strip().lower()

    if not domain or "." not in domain or " " in domain or "://" in domain:
        return render_domain(site, domain_error="Enter a valid domain name.")

    if is_domain_taken(domain, exclude_user_id=site["id"]):
        return render_domain(site, domain_error="That domain is already in use.")

    token = secrets.token_urlsafe(24)
    set_custom_domain(site["id"], domain, token)
    site = get_user_by_id(site["id"])
    return render_domain(site)


@app.route("/-/settings/domain/verify", methods=["POST"])
def settings_domain_verify():
    site = require_owner()

    if not site.get("custom_domain") or not site.get("domain_verification_token"):
        return redirect("/-/settings/domain")

    domain = site["custom_domain"]
    token = site["domain_verification_token"]

    try:
        answers = dns.resolver.resolve(f"_tinypost.{domain}", "TXT")
        found = any(f"tinypost-site-verification={token}" in str(r) for r in answers)
    except Exception:
        found = False

    if not found:
        return render_domain(
            site, domain_error="TXT record not found. It may take a few minutes to propagate."
        )

    verify_custom_domain(site["id"])
    flash("Domain verified.")
    return redirect("/-/settings")


@app.route("/-/settings/domain/remove", methods=["POST"])
def settings_domain_remove():
    site = require_owner()
    remove_custom_domain(site["id"])
    return redirect("/-/settings/domain")


@app.route("/-/settings/delete-account", methods=["GET", "POST"])
def settings_delete_account():
    site = require_owner()

    if request.method == "GET":
        return render_template("delete_account.html", site=site, is_owner=True)

    if request.form.get("confirmation") != "delete":
        return render_template(
            "delete_account.html",
            site=site,
            is_owner=True,
            error="Type 'delete' to confirm.",
        )

    delete_all_images(site["subdomain"])
    delete_account(session["user_id"])
    session.clear()
    return redirect(f"http://{app.config['BASE_DOMAIN']}")


# ── Welcome (post-signup onboarding) ─────────


@app.route("/-/welcome/photo", methods=["GET", "POST"])
def welcome_photo():
    site = require_owner()
    if request.method == "GET":
        return render_template("welcome_photo.html", site=site, is_owner=True)

    file = request.files.get("avatar")
    if file:
        error = validate_image(file)
        if error:
            return render_template("welcome_photo.html", site=site, is_owner=True, error=error)
        ext = ALLOWED_IMAGE_TYPES[file.content_type]
        fmt = file.content_type.split("/")[-1].upper()
        cropped = crop_square(file, fmt)
        key = f"{site['subdomain']}/avatar.{ext}"
        url = upload_image(key, cropped, file.content_type)
        update_user_avatar(site["id"], url)
    return redirect("/-/welcome/bio")


@app.route("/-/welcome/bio", methods=["GET", "POST"])
def welcome_bio():
    site = require_owner()
    if request.method == "GET":
        return render_template("welcome_bio.html", site=site, is_owner=True)

    bio = request.form.get("bio", "").strip()
    if bio:
        update_user_blog(site["id"], site["title"], bio)
    return redirect("/-/edit")
