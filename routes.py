import os
import uuid
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import format_datetime

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
from config import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE
from db import (
    create_post,
    create_user_and_site,
    delete_post,
    get_post_by_slug,
    get_posts_for_site,
    get_site_by_subdomain,
    get_site_by_user,
    get_user_by_email,
    get_user_by_id,
    subdomain_taken,
    update_post,
    update_site,
    update_site_avatar,
)
from storage import crop_square, delete_image, file_size, upload_image
from utils import is_valid_subdomain, mask_email, site_url, slugify

CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
SOURCE_NS = "http://source.scripting.com/"
ET.register_namespace("content", CONTENT_NS)
ET.register_namespace("source", SOURCE_NS)


def get_current_site():
    host = request.host.split(":")[0]
    base = app.config["BASE_DOMAIN"].split(":")[0]
    if not host.endswith("." + base):
        return None
    subdomain = host.replace("." + base, "")
    return get_site_by_subdomain(subdomain)


def require_owner():
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["user_id"]:
        abort(redirect("/signin"))
    return site


@app.route("/", methods=["GET", "POST"])
def home():
    host = request.host.split(":")[0]
    base = app.config["BASE_DOMAIN"].split(":")[0]

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
            user_site_url=site_url(site) if user and site else None,
        )

    site = get_current_site()
    if not site:
        abort(404)
    is_owner = session.get("user_id") == site["user_id"]
    posts = get_posts_for_site(site["id"], include_drafts=is_owner)
    return render_template("site.html", site=site, posts=posts, is_owner=is_owner)


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
    return redirect(site_url(site))


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
    return redirect(site_url(site))


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
    is_draft = request.form.get("is_draft") == "on"
    create_post(site["id"], slug, title or None, body, is_draft=is_draft)
    return redirect(f"/{slug}")


@app.route("/edit/<slug>", methods=["GET", "POST"])
def edit_post(slug):
    site = require_owner()
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


@app.route("/settings", methods=["GET", "POST"])
def settings():
    site = require_owner()

    if request.method == "GET":
        return render_template("settings.html", site=site)

    title = request.form.get("title", "").strip()
    bio = request.form.get("bio", "").strip()
    if not title:
        return render_template("settings.html", site=site, error="Title is required.")
    update_site(site["id"], title, bio or None)
    return redirect("/")


@app.route("/settings/avatar", methods=["POST"])
def settings_avatar():
    site = require_owner()

    file = request.files.get("avatar")
    if not file:
        return redirect("/settings")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return render_template("settings.html", site=site, error="File type not allowed.")

    if file_size(file) > MAX_IMAGE_SIZE:
        return render_template("settings.html", site=site, error="File too large (max 5MB).")

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


@app.route("/<slug>")
def post(slug):
    site = get_current_site()
    if not site:
        abort(404)
    post = get_post_by_slug(site["id"], slug)
    if not post:
        abort(404)
    is_owner = session.get("user_id") == site["user_id"]
    if post["is_draft"] and not is_owner:
        abort(404)
    return render_template("post.html", site=site, post=post, is_owner=is_owner)


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
