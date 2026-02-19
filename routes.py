import io
import os
import secrets
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import timezone
from email.utils import format_datetime

import dns.resolver
import markdown as md
from flask import (
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
)

from app import app
from auth import generate_passcode, send_passcode
from config import (
    ALLOWED_IMAGE_TYPES,
    CADDY_ASK_TOKEN,
    COLOR_RE,
    CUSTOM_DOMAIN_IPV4,
    CUSTOM_DOMAIN_IPV6,
    FONT_OPTIONS,
    MAX_IMAGE_SIZE,
    VALID_FONT_VALUES,
)
from db import (
    confirm_subscriber,
    create_page,
    create_post,
    create_subscriber,
    create_user_and_site,
    delete_account,
    delete_page,
    delete_post,
    delete_subscriber,
    get_all_posts_for_site,
    get_all_subscribers,
    get_confirmed_subscribers,
    get_page_by_id,
    get_page_by_slug,
    get_pages_for_site,
    get_post_by_slug,
    get_posts_for_site,
    get_site_by_custom_domain,
    get_site_by_id,
    get_site_by_subdomain,
    get_site_by_user,
    get_subscriber,
    get_subscriber_by_token,
    get_subscriber_count,
    get_user_by_email,
    get_user_by_id,
    is_domain_taken,
    mark_post_sent,
    remove_custom_domain,
    reorder_pages,
    set_custom_domain,
    subdomain_taken,
    unsubscribe,
    update_page,
    update_post,
    update_site,
    update_site_avatar,
    update_site_custom_css,
    update_site_design,
    update_subscriber_token,
    update_user_email,
    verify_custom_domain,
)
from mailer import send_email
from storage import (
    crop_square,
    delete_all_images,
    delete_image,
    download_image,
    file_size,
    list_images,
    upload_image,
)
from utils import auto_text_color, is_valid_subdomain, mask_email, site_url, slugify, subdomain_url

CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
SOURCE_NS = "http://source.scripting.com/"
ET.register_namespace("content", CONTENT_NS)
ET.register_namespace("source", SOURCE_NS)


def render_settings(site, **kwargs):
    return render_template(
        "settings.html",
        site=site,
        is_owner=True,
        custom_domain_ipv4=CUSTOM_DOMAIN_IPV4,
        custom_domain_ipv6=CUSTOM_DOMAIN_IPV6,
        **kwargs,
    )


def render_account(site, user, **kwargs):
    return render_template("account.html", site=site, user=user, is_owner=True, **kwargs)


def host_and_base():
    host = request.host.split(":")[0]
    base = app.config["BASE_DOMAIN"].split(":")[0]
    return host, base


def get_current_site():
    host, base = host_and_base()
    suffix = "." + base
    if host.endswith(suffix):
        subdomain = host.removesuffix(suffix)
        return get_site_by_subdomain(subdomain)
    if host != base:
        return get_site_by_custom_domain(host)
    return None


def require_owner():
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        abort(redirect("/signin"))
    return site


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
    )


@app.route("/check-subdomain")
def check_subdomain():
    name = request.args.get("name", "").lower().strip()
    if not is_valid_subdomain(name):
        return jsonify({"error": "Invalid name"})
    if subdomain_taken(name):
        return jsonify({"available": False})
    return jsonify({"available": True})


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
    return redirect(subdomain_url(site))


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
    return redirect(subdomain_url(site))


@app.route("/edit", methods=["GET", "POST"])
def edit():
    site = require_owner()

    if request.method == "GET":
        return render_template("edit.html", site=site)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not body:
        return render_template("edit.html", site=site, error="Post body is required.")
    slug = slugify(title or body[:50]) or "post"
    if get_page_by_slug(site["id"], slug):
        return render_template("edit.html", site=site, error="A page already uses that URL slug.")
    is_draft = request.form.get("is_draft") == "on"
    create_post(site["id"], slug, title or None, body, is_draft=is_draft)
    return redirect(f"/{slug}")


@app.route("/edit/<slug>", methods=["GET", "POST"])
def edit_post(slug):
    site = require_owner()
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)

    sub_count = get_subscriber_count(site["id"])

    if request.method == "GET":
        return render_template("edit.html", site=site, post=post, subscriber_count=sub_count)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not body:
        return render_template(
            "edit.html",
            site=site,
            post=post,
            subscriber_count=sub_count,
            error="Post body is required.",
        )
    new_slug = slugify(title or body[:50]) or "post"
    if get_page_by_slug(site["id"], new_slug):
        return render_template(
            "edit.html",
            site=site,
            post=post,
            subscriber_count=sub_count,
            error="A page already uses that URL slug.",
        )
    is_draft = request.form.get("is_draft") == "on"
    update_post(post["id"], new_slug, title or None, body, is_draft=is_draft)
    return redirect(f"/{new_slug}")


@app.route("/delete/<slug>", methods=["POST"])
def delete_post_route(slug):
    site = require_owner()
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    delete_post(post["id"])
    return redirect("/")


@app.route("/send/<slug>", methods=["POST"])
def send_post(slug):
    site = require_owner()
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    if post["is_draft"] or post.get("sent_at"):
        return redirect(f"/edit/{slug}")

    subscribers = get_confirmed_subscribers(site["id"])
    if not subscribers:
        return redirect(f"/edit/{slug}")

    base_url = site_url(site)
    for sub in subscribers:
        send_email(
            to=sub["email"],
            from_addr="Jottit <noreply@jottit.pub>",
            subject=post["title"] or site["title"],
            text=(
                f"{post['title'] or ''}\n\n"
                f"{post['body']}\n\n"
                f"---\n"
                f"You're receiving this because you subscribed to {site['title']}.\n"
                f"Unsubscribe: {base_url}/unsubscribe/{sub['token']}"
            ),
        )

    mark_post_sent(post["id"])
    return redirect(f"/{slug}")


@app.route("/subscribers")
def subscribers():
    site = require_owner()
    subs = get_all_subscribers(site["id"])
    confirmed = sum(1 for s in subs if s["confirmed"])
    pending = len(subs) - confirmed
    return render_template(
        "subscribers.html",
        site=site,
        subscribers=subs,
        total=len(subs),
        confirmed_count=confirmed,
        pending_count=pending,
        is_owner=True,
    )


@app.route("/subscribers/delete/<int:subscriber_id>", methods=["POST"])
def subscribers_delete(subscriber_id):
    site = require_owner()
    delete_subscriber(subscriber_id, site["id"])
    return redirect("/subscribers")


@app.route("/settings", methods=["GET", "POST"])
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

    update_site(site["id"], title, bio or None, license=license, social_links=social_links)
    return redirect("/")


@app.route("/settings/avatar", methods=["POST"])
def settings_avatar():
    site = require_owner()

    file = request.files.get("avatar")
    if not file:
        return redirect("/settings")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return render_settings(site, error="File type not allowed.")

    if file_size(file) > MAX_IMAGE_SIZE:
        return render_settings(site, error="File too large (max 5MB).")

    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    fmt = file.content_type.split("/")[-1].upper()
    cropped = crop_square(file, fmt)
    key = f"{site['subdomain']}/avatar.{ext}"
    url = upload_image(key, cropped, file.content_type)
    update_site_avatar(site["id"], url)
    return redirect("/settings")


@app.route("/settings/avatar/delete", methods=["POST"])
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
    return redirect("/settings")


@app.route("/settings/export")
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


@app.route("/settings/domain", methods=["POST"])
def settings_domain():
    site = require_owner()
    domain = request.form.get("domain", "").strip().lower()

    if not domain or "." not in domain or " " in domain or "://" in domain:
        return render_settings(site, domain_error="Enter a valid domain name.")

    if is_domain_taken(domain, exclude_site_id=site["id"]):
        return render_settings(site, domain_error="That domain is already in use.")

    token = secrets.token_urlsafe(24)
    set_custom_domain(site["id"], domain, token)
    return redirect("/settings")


@app.route("/settings/domain/verify", methods=["POST"])
def settings_domain_verify():
    site = require_owner()

    if not site.get("custom_domain") or not site.get("domain_verification_token"):
        return redirect("/settings")

    domain = site["custom_domain"]
    token = site["domain_verification_token"]

    try:
        answers = dns.resolver.resolve(f"_jottit.{domain}", "TXT")
        found = any(f"jottit-site-verification={token}" in str(r) for r in answers)
    except Exception:
        found = False

    if not found:
        return render_settings(
            site, domain_error="TXT record not found. It may take a few minutes to propagate."
        )

    verify_custom_domain(site["id"])
    return redirect("/settings")


@app.route("/settings/domain/remove", methods=["POST"])
def settings_domain_remove():
    site = require_owner()
    remove_custom_domain(site["id"])
    return redirect("/settings")


@app.route("/account", methods=["GET", "POST"])
def account():
    site = require_owner()
    user = get_user_by_id(session["user_id"])

    if request.method == "GET":
        return render_account(site, user)

    email = request.form.get("email", "").strip().lower()
    if not email:
        return render_account(site, user, error="Email is required.")
    update_user_email(user["id"], email)
    user = get_user_by_id(user["id"])
    return render_account(site, user, success="Email updated.")


@app.route("/design", methods=["GET", "POST"])
def design():
    site = require_owner()
    d = site["design"] or {}

    if request.method == "GET":
        return render_template(
            "design.html",
            site=site,
            is_owner=True,
            design=d,
            font_options=FONT_OPTIONS,
        )

    font_header = request.form.get("font_header", "").strip()
    font_body = request.form.get("font_body", "").strip()
    color_accent = request.form.get("color_accent", "").strip()
    color_bg = request.form.get("color_bg", "").strip()
    color_text = request.form.get("color_text", "").strip()

    if font_header not in VALID_FONT_VALUES:
        font_header = ""
    if font_body not in VALID_FONT_VALUES:
        font_body = ""

    for c in (color_accent, color_bg, color_text):
        if c and not COLOR_RE.match(c):
            return render_template(
                "design.html",
                site=site,
                is_owner=True,
                design=d,
                font_options=FONT_OPTIONS,
                error="Invalid color value.",
            )

    if color_bg and not color_text:
        color_text = auto_text_color(color_bg)
    if not color_bg:
        color_text = ""

    fields = {
        "font_header": font_header,
        "font_body": font_body,
        "color_accent": color_accent,
        "color_bg": color_bg,
        "color_text": color_text,
    }
    design_data = {k: v for k, v in fields.items() if v}
    update_site_design(site["id"], design_data or None)
    return redirect("/")


@app.route("/download-theme")
def download_theme():
    site = require_owner()
    custom_css = site.get("custom_css")

    header = f"""\
/*
 * Theme: {"Custom" if custom_css else "Default"}
 * Author: {site["title"]}
 * Site: {site_url(site)}
 * Version: 1.0
 * License: {site.get("license") or ""}
 */

"""

    if custom_css:
        body = custom_css
    else:
        theme_path = os.path.join(app.static_folder, "theme.css")
        with open(theme_path) as f:
            body = f.read()

    return Response(
        header + body,
        mimetype="text/css",
        headers={"Content-Disposition": 'attachment; filename="theme.css"'},
    )


@app.route("/design/upload-css", methods=["POST"])
def upload_css():
    site = require_owner()

    css_file = request.files.get("css_file")
    if not css_file:
        return redirect("/design")

    content = css_file.read().decode("utf-8", errors="replace").strip()
    if not content:
        return redirect("/design")

    update_site_custom_css(site["id"], content)
    return redirect("/design")


@app.route("/design/remove-css", methods=["POST"])
def remove_css():
    site = require_owner()
    update_site_custom_css(site["id"], None)
    return redirect("/design")


@app.route("/settings/navigation/add", methods=["POST"])
def settings_navigation_add():
    site = require_owner()
    if request.is_json:
        title = (request.get_json().get("title") or "").strip()
    else:
        title = request.form.get("title", "").strip()
    slug = slugify(title) if title else None

    error = None
    error_status = 400
    if not slug:
        error = "Title is required."
    elif get_post_by_slug(site["id"], slug) or get_page_by_slug(site["id"], slug):
        error = "That URL slug is already taken."
        error_status = 409

    if error:
        if request.is_json:
            return jsonify({"error": error}), error_status
        return render_settings(site, nav_error=error)

    create_page(site["id"], slug, title)
    if request.is_json:
        return jsonify({"slug": slug})
    return redirect(f"/edit-page/{slug}")


@app.route("/settings/navigation/delete/<int:page_id>", methods=["POST"])
def settings_navigation_delete(page_id):
    site = require_owner()
    page = get_page_by_id(page_id)
    if not page or page["site_id"] != site["id"]:
        abort(404)
    delete_page(page_id)
    if request.is_json:
        return jsonify({"ok": True})
    return redirect("/")


@app.route("/settings/navigation/reorder", methods=["POST"])
def settings_navigation_reorder():
    site = require_owner()
    data = request.get_json()
    if not data or "order" not in data:
        return jsonify({"error": "Missing order"}), 400
    reorder_pages(site["id"], data["order"])
    return jsonify({"ok": True})


@app.route("/new-page", methods=["GET", "POST"])
def new_page():
    site = require_owner()

    if request.method == "GET":
        title = request.args.get("title", "").strip()
        page = {"title": title, "body": "", "is_draft": False}
        return render_template("edit_page.html", site=site, page=page, new=True)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    slug = slugify(title) if title else None
    page = {"title": title, "body": body, "is_draft": False}

    if not slug:
        return render_template(
            "edit_page.html", site=site, page=page, new=True, error="Title is required."
        )
    if get_post_by_slug(site["id"], slug) or get_page_by_slug(site["id"], slug):
        return render_template(
            "edit_page.html",
            site=site,
            page=page,
            new=True,
            error="That URL slug is already taken.",
        )
    is_draft = request.form.get("is_draft") == "on"
    create_page(site["id"], slug, title, body=body, is_draft=is_draft)
    return redirect(f"/{slug}")


@app.route("/edit-page/<slug>", methods=["GET", "POST"])
def edit_page(slug):
    site = require_owner()
    page = get_page_by_slug(site["id"], slug)
    if not page:
        abort(404)

    if request.method == "GET":
        return render_template("edit_page.html", site=site, page=page)

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title:
        return render_template("edit_page.html", site=site, page=page, error="Title is required.")
    is_draft = request.form.get("is_draft") == "on"
    update_page(page["id"], title, body, is_draft=is_draft)
    return redirect(f"/{page['slug']}")


@app.route("/settings/delete-account", methods=["GET", "POST"])
def settings_delete_account():
    site = require_owner()

    if request.method == "GET":
        return render_template("delete_account.html", site=site, is_owner=True)

    if request.form.get("confirmation") != "delete":
        return render_template(
            "delete_account.html", site=site, is_owner=True, error="Type 'delete' to confirm."
        )

    delete_all_images(site["subdomain"])
    delete_account(session["user_id"])
    session.clear()
    return redirect(f"http://{app.config['BASE_DOMAIN']}")


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


@app.route("/feed.xml")
def feed():
    site = get_current_site()
    if not site:
        abort(404)
    posts = get_posts_for_site(site["id"])[:20]
    base_url = site_url(site)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = site["title"]
    ET.SubElement(channel, "link").text = base_url
    ET.SubElement(channel, "description").text = site["bio"] or site["title"]
    if site["avatar"]:
        image = ET.SubElement(channel, "image")
        ET.SubElement(image, "url").text = site["avatar"]
        ET.SubElement(image, "title").text = site["title"]
        ET.SubElement(image, "link").text = base_url
    if posts:
        last_build = posts[0]["created_at"].replace(tzinfo=timezone.utc)
        ET.SubElement(channel, "lastBuildDate").text = format_datetime(last_build)

    for p in posts:
        item = ET.SubElement(channel, "item")
        permalink = f"{base_url}/{p['slug']}"
        ET.SubElement(item, "title").text = p["title"] or ""
        ET.SubElement(item, "link").text = permalink
        ET.SubElement(item, "guid").text = permalink
        pub_date = p["created_at"].replace(tzinfo=timezone.utc)
        ET.SubElement(item, "pubDate").text = format_datetime(pub_date)
        html = md.markdown(p["body"])
        ET.SubElement(item, "description").text = html
        ET.SubElement(item, f"{{{CONTENT_NS}}}encoded").text = html
        ET.SubElement(item, f"{{{SOURCE_NS}}}markdown").text = p["body"]

    xml_str = ET.tostring(rss, encoding="unicode", xml_declaration=False)
    xml_out = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    return Response(xml_out, content_type="application/rss+xml; charset=utf-8")


@app.route("/feed.json")
def feed_json():
    site = get_current_site()
    if not site:
        abort(404)
    posts = get_posts_for_site(site["id"])[:20]
    base_url = site_url(site)

    items = []
    for p in posts:
        permalink = f"{base_url}/{p['slug']}"
        items.append(
            {
                "id": permalink,
                "url": permalink,
                "title": p["title"] or "",
                "content_html": md.markdown(p["body"]),
                "content_text": p["body"],
                "date_published": p["created_at"].replace(tzinfo=timezone.utc).isoformat(),
            }
        )

    data = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": site["title"],
        "home_page_url": base_url,
        "feed_url": f"{base_url}/feed.json",
        "items": items,
    }
    if site["avatar"]:
        data["icon"] = site["avatar"]
    response = jsonify(data)
    response.content_type = "application/feed+json; charset=utf-8"
    return response


@app.route("/subscribe", methods=["POST"])
def subscribe():
    site = get_current_site()
    if not site:
        abort(404)

    if request.form.get("website"):
        return render_template("subscribed.html", site=site)

    email = request.form.get("email", "").strip().lower()
    if not email:
        return redirect("/")

    token = secrets.token_urlsafe(32)
    existing = get_subscriber(site["id"], email)
    if existing:
        if existing["confirmed"]:
            return render_template("subscribed.html", site=site)
        update_subscriber_token(existing["id"], token)
    else:
        create_subscriber(site["id"], email, token)

    base_url = site_url(site)
    confirm_url = f"{base_url}/confirm/{token}"
    send_email(
        to=email,
        subject=f"Please confirm your subscription to {site['title']}",
        from_addr="Jottit <confirm-subscriber@jottit.pub>",
        text=(
            f"You're almost subscribed to updates from {site['title']}.\n\n"
            f"Confirm your subscription below to get future posts in your inbox.\n\n"
            f"{confirm_url}\n\n"
            f"---\n"
            f"Don't want to subscribe? Feel free to ignore this email."
        ),
        html=render_template(
            "email_confirm_subscription.html",
            site=site,
            confirm_url=confirm_url,
        ),
    )
    return render_template("subscribed.html", site=site)


@app.route("/confirm/<token>")
def confirm(token):
    subscriber = get_subscriber_by_token(token)
    if not subscriber:
        abort(404)
    confirm_subscriber(token)
    site = get_site_by_id(subscriber["site_id"])
    return render_template(
        "confirmed.html",
        site=site,
        token=token,
        base_url=site_url(site),
    )


@app.route("/unsubscribe/<token>")
def unsubscribe_route(token):
    subscriber = get_subscriber_by_token(token)
    if not subscriber:
        abort(404)
    site = get_site_by_id(subscriber["site_id"])
    unsubscribe(token)
    return render_template("unsubscribed.html", site=site, base_url=site_url(site))


@app.route("/<slug>")
def post(slug):
    site = get_current_site()
    if not site:
        abort(404)
    is_owner = session.get("user_id") == site["user_id"]
    pages = get_pages_for_site(site["id"], include_drafts=is_owner)

    post = get_post_by_slug(site["id"], slug)
    if post:
        if post["is_draft"] and not is_owner:
            abort(404)
        return render_template(
            "post.html",
            site=site,
            post=post,
            pages=pages,
            is_owner=is_owner,
            subscriber_count=get_subscriber_count(site["id"]) if is_owner else 0,
        )

    page = get_page_by_slug(site["id"], slug)
    if page:
        if page["is_draft"] and not is_owner:
            abort(404)
        return render_template("page.html", site=site, page=page, pages=pages, is_owner=is_owner)

    abort(404)


@app.route("/upload", methods=["POST"])
def upload():
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        return jsonify({"error": "Unauthorized"}), 401

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return jsonify({"error": "File type not allowed"}), 400

    if file_size(file) > MAX_IMAGE_SIZE:
        return jsonify({"error": "File too large (max 5MB)"}), 400

    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    key = f"{site['subdomain']}/{uuid.uuid4()}.{ext}"

    url = upload_image(key, file, file.content_type)
    return jsonify({"url": url})


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.instance_path, "uploads"), filename)


@app.route("/signout", methods=["POST"])
def signout():
    session.clear()
    return redirect("/")
