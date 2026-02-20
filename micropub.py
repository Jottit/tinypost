import uuid

from flask import abort, jsonify, request
from markdownify import markdownify

from app import app
from config import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE
from db import create_post, get_post_by_slug
from indieauth_db import get_token
from storage import file_size, upload_image
from utils import get_current_site, site_url, slugify, subdomain_url


def _verify_token(site):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, (jsonify({"error": "unauthorized"}), 401)
    token_str = auth[7:]
    token = get_token(token_str)
    if not token or token["site_id"] != site["id"]:
        return None, (jsonify({"error": "unauthorized"}), 401)
    if "create" not in token["scope"].split():
        return None, (jsonify({"error": "insufficient_scope"}), 403)
    return token, None


def _first(values):
    if isinstance(values, list):
        return values[0] if values else ""
    return values


def _html_to_markdown(html):
    return markdownify(html, heading_style="ATX").strip()


def _unwrap_content(value):
    value = _first(value)
    if isinstance(value, dict):
        html = value.get("html", "")
        if html:
            return _html_to_markdown(html)
        return value.get("value", "")
    return value


def _parse_entry():
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json(silent=True) or {}
        props = data.get("properties", {})
        return {
            "name": _first(props.get("name", "")),
            "content": _unwrap_content(props.get("content", "")),
            "post_status": _first(props.get("post-status", "")),
            "slug": _first(props.get("mp-slug", "")),
        }
    html = request.form.get("content[html]", "")
    return {
        "name": request.form.get("name", ""),
        "content": _html_to_markdown(html) if html else request.form.get("content", ""),
        "post_status": request.form.get("post-status", ""),
        "slug": request.form.get("mp-slug", ""),
    }


def _generate_slug(title):
    return (title and slugify(title)) or uuid.uuid4().hex[:8]


@app.route("/micropub", methods=["POST"])
def micropub_post():
    site = get_current_site()
    if not site:
        abort(404)

    token, err = _verify_token(site)
    if err:
        return err

    entry = _parse_entry()
    title = entry["name"]
    body = entry["content"]
    if not title and body.startswith("# "):
        first_line, _, rest = body.partition("\n")
        title = first_line[2:].strip()
        body = rest.lstrip("\n")
    is_draft = entry["post_status"] == "draft"

    slug = entry["slug"] or _generate_slug(title)
    existing = get_post_by_slug(site["id"], slug)
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    post = create_post(site["id"], slug, title, body, is_draft=is_draft)

    location = f"{subdomain_url(site)}/{post['slug']}"
    return "", 201, {"Location": location}


@app.route("/micropub", methods=["GET"])
def micropub_query():
    site = get_current_site()
    if not site:
        abort(404)

    token, err = _verify_token(site)
    if err:
        return err

    q = request.args.get("q", "")

    if q in ("config", "syndicate-to"):
        return jsonify({"syndicate-to": []})

    if q == "source":
        url = request.args.get("url", "")
        base = site_url(site)
        if not url.startswith(base + "/"):
            return jsonify({"error": "invalid_request"}), 400
        slug = url[len(base) + 1 :]
        post = get_post_by_slug(site["id"], slug)
        if not post:
            return jsonify({"error": "invalid_request"}), 400
        props = {"content": [post["body"]]}
        if post["title"]:
            props["name"] = [post["title"]]
        if post["is_draft"]:
            props["post-status"] = ["draft"]
        return jsonify({"type": ["h-entry"], "properties": props})

    return jsonify({"error": "invalid_request"}), 400


@app.route("/micropub/media", methods=["POST"])
def micropub_media():
    site = get_current_site()
    if not site:
        abort(404)

    token, err = _verify_token(site)
    if err:
        return err

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "invalid_request", "error_description": "No file provided"}), 400

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return (
            jsonify(
                {"error": "invalid_request", "error_description": "File type not allowed"},
            ),
            400,
        )

    if file_size(file) > MAX_IMAGE_SIZE:
        return jsonify({"error": "invalid_request", "error_description": "File too large"}), 400

    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    key = f"{site['subdomain']}/{uuid.uuid4()}.{ext}"
    url = upload_image(key, file, file.content_type)
    return "", 201, {"Location": url}
