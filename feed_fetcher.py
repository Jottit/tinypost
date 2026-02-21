import logging
import os
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


def fetch_feed(feed_url):
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        raise ValueError(f"Failed to parse feed: {feed.bozo_exception}")

    result = {
        "feed_title": getattr(feed.feed, "title", None),
        "latest_post_title": None,
        "last_updated": None,
        "feed_icon_url": None,
    }

    if feed.entries:
        entry = feed.entries[0]
        result["latest_post_title"] = getattr(entry, "title", None)

        time_struct = getattr(entry, "published_parsed", None) or getattr(
            entry, "updated_parsed", None
        )
        if time_struct:
            result["last_updated"] = datetime(*time_struct[:6], tzinfo=timezone.utc)

    result["feed_icon_url"] = _find_favicon(feed_url, feed)

    return result


def _find_favicon(feed_url, feed):
    domain = urlparse(feed_url).netloc
    favicon_url = f"https://{domain}/favicon.ico"

    try:
        req = urllib.request.Request(favicon_url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=10)
        content_type = resp.headers.get("Content-Type", "")
        if resp.status == 200 and "image" in content_type:
            return favicon_url
    except Exception:
        pass

    image = getattr(feed.feed, "image", None)
    if image:
        href = getattr(image, "href", None)
        if href:
            return href

    return None


def refresh_all_feeds():
    database_url = os.environ.get("DATABASE_URL", "postgresql://localhost/jottit")
    conn = psycopg.connect(database_url, row_factory=dict_row)
    try:
        rows = conn.execute(
            "SELECT id, feed_url FROM blogroll WHERE feed_url IS NOT NULL"
        ).fetchall()

        for row in rows:
            now = datetime.now(timezone.utc)
            try:
                data = fetch_feed(row["feed_url"])
                conn.execute(
                    "UPDATE blogroll SET feed_title = %s, feed_icon_url = %s,"
                    " latest_post_title = %s, last_updated = %s, last_fetched = %s"
                    " WHERE id = %s",
                    (
                        data["feed_title"],
                        data["feed_icon_url"],
                        data["latest_post_title"],
                        data["last_updated"],
                        now,
                        row["id"],
                    ),
                )
                conn.commit()
            except Exception:
                logger.exception("Failed to fetch feed %s", row["feed_url"])
                conn.execute(
                    "UPDATE blogroll SET last_fetched = %s WHERE id = %s",
                    (now, row["id"]),
                )
                conn.commit()
    finally:
        conn.close()
