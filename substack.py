import csv
import io
from datetime import datetime

from markdownify import markdownify

from db import get_db, get_post_by_slug


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

        slug = row.get("slug", "").strip()
        post_id = row.get("post_id", "").strip()
        if not slug or not post_id:
            continue

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
