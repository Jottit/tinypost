import csv
import io
import re
import secrets
import uuid
from datetime import datetime
from urllib.request import urlopen

from markdownify import markdownify

from config import ALLOWED_IMAGE_TYPES
from db import get_all_posts_for_site, get_db, get_post_by_slug, get_subscriber
from storage import upload_image

SUBSTACK_CDN_RE = re.compile(
    r"https?://(?:substackcdn\.com|substack-post-media\.s3\.amazonaws\.com)/[^\s\)]+"
)


def find_in_zip(zf, suffix):
    for name in zf.namelist():
        if name == suffix or name.endswith(f"/{suffix}"):
            return name
    return None


def import_posts(zf, site_id):
    csv_path = find_in_zip(zf, "posts.csv")
    if not csv_path:
        return {"posts_imported": 0, "posts_skipped": 0}

    reader = csv.DictReader(io.StringIO(zf.read(csv_path).decode("utf-8")))
    db = get_db()
    imported = 0
    skipped = 0

    for row in reader:
        if row.get("is_published") != "true":
            continue

        post_id = row.get("post_id", "").strip()
        if not post_id or "." not in post_id:
            continue
        slug = post_id.split(".", 1)[1]

        if get_post_by_slug(site_id, slug):
            skipped += 1
            continue

        html_path = find_in_zip(zf, f"{post_id}.html")
        if not html_path:
            skipped += 1
            continue

        html = zf.read(html_path).decode("utf-8")
        body = markdownify(html, heading_style="ATX").strip()
        title = row.get("title", "").strip() or None

        published_at = None
        post_date = row.get("post_date", "").strip()
        if post_date:
            try:
                published_at = datetime.fromisoformat(post_date)
            except ValueError:
                pass

        db.execute(
            "INSERT INTO posts (site_id, slug, title, body, published_at)"
            " VALUES (%s, %s, %s, %s, %s)",
            (site_id, slug, title, body, published_at),
        )
        imported += 1

    db.commit()
    return {"posts_imported": imported, "posts_skipped": skipped}


def rehost_images(site_id, subdomain):
    posts = get_all_posts_for_site(site_id)
    db = get_db()
    url_map = {}
    rehosted = 0

    for post in posts:
        body = post["body"]
        urls = set(SUBSTACK_CDN_RE.findall(body))
        if not urls:
            continue

        for url in urls:
            if url in url_map:
                body = body.replace(url, url_map[url])
                continue
            try:
                with urlopen(url, timeout=30) as resp:
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                    ext = ALLOWED_IMAGE_TYPES.get(content_type, "jpg")
                    key = f"{subdomain}/{uuid.uuid4()}.{ext}"
                    new_url = upload_image(key, io.BytesIO(resp.read()), content_type)
                url_map[url] = new_url
                body = body.replace(url, new_url)
                rehosted += 1
            except Exception:
                continue

        if body != post["body"]:
            db.execute(
                "UPDATE posts SET body = %s WHERE id = %s",
                (body, post["id"]),
            )

    db.commit()
    return rehosted


def import_subscribers(zf, site_id):
    csv_path = None
    for name in zf.namelist():
        basename = name.rsplit("/", 1)[-1].lower()
        if basename.endswith(".csv") and (
            "subscribers" in basename or basename.startswith("email_list")
        ):
            csv_path = name
            break

    if not csv_path:
        return {"subscribers_imported": 0, "subscribers_skipped": 0}

    reader = csv.DictReader(io.StringIO(zf.read(csv_path).decode("utf-8")))
    db = get_db()
    imported = 0
    skipped = 0

    for row in reader:
        email = row.get("email", "").strip().lower()
        if not email:
            continue

        if row.get("active_subscription", "").strip().lower() == "paid":
            skipped += 1
            continue

        if get_subscriber(site_id, email):
            skipped += 1
            continue

        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO subscribers (site_id, email, token, confirmed)"
            " VALUES (%s, %s, %s, TRUE)",
            (site_id, email, token),
        )
        imported += 1

    db.commit()
    return {"subscribers_imported": imported, "subscribers_skipped": skipped}
