import logging
import os
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import feedparser
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.feeds = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        attrs_dict = dict(attrs)
        rel = attrs_dict.get("rel", "")
        if rel != "alternate":
            return
        feed_type = attrs_dict.get("type", "")
        if feed_type in ("application/rss+xml", "application/atom+xml"):
            href = attrs_dict.get("href")
            if href:
                self.feeds.append(href)


def discover_feed_url(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tinypost/1.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None

    parser = _LinkParser()
    try:
        parser.feed(html)
    except Exception:
        return None

    if not parser.feeds:
        return None

    href = parser.feeds[0]
    return urljoin(url, href)


def fetch_feed(feed_url):
    req = urllib.request.Request(feed_url, headers={"User-Agent": "Tinypost/1.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    content = resp.read()
    feed = feedparser.parse(content)

    if feed.bozo and not feed.entries:
        raise ValueError(f"Failed to parse feed: {feed.bozo_exception}")

    result = {
        "feed_title": getattr(feed.feed, "title", None),
        "latest_post_title": None,
        "latest_post_url": None,
        "last_updated": None,
        "feed_icon_url": None,
    }

    if feed.entries:
        entry = feed.entries[0]
        title = getattr(entry, "title", None)
        if not title:
            desc = getattr(entry, "summary", None) or ""
            text = re.sub(r"<[^>]+>", "", desc).strip()
            if text:
                words = text.split()
                title = " ".join(words[:10])
                if len(words) > 10:
                    title += "…"
        result["latest_post_title"] = title or None
        result["latest_post_url"] = getattr(entry, "link", None)

        time_struct = getattr(entry, "published_parsed", None) or getattr(
            entry, "updated_parsed", None
        )
        if time_struct:
            dt = datetime(*time_struct[:6], tzinfo=timezone.utc)
            result["last_updated"] = min(dt, datetime.now(timezone.utc))

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
    if image and getattr(image, "href", None):
        return image.href

    return None


def refresh_all_feeds(url=None):
    database_url = os.environ.get("DATABASE_URL", "postgresql://localhost/tinypost")
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        if url:
            url_filter = " AND f.url = %s"
            url_params = (url,)
        else:
            url_filter = ""
            url_params = ()

        missing = conn.execute(
            "SELECT f.id, f.url FROM feeds f"
            " WHERE (f.feed_url IS NULL OR f.feed_url = '')" + url_filter,
            url_params,
        ).fetchall()

        for row in missing:
            feed_url = discover_feed_url(row["url"])
            if feed_url:
                conn.execute(
                    "UPDATE feeds SET feed_url = %s WHERE id = %s",
                    (feed_url, row["id"]),
                )
                conn.commit()

        rows = conn.execute(
            "SELECT DISTINCT f.id, f.feed_url FROM feeds f"
            " JOIN blogroll b ON b.feed_id = f.id"
            " WHERE f.feed_url IS NOT NULL AND f.feed_url != ''" + url_filter,
            url_params,
        ).fetchall()

        for row in rows:
            now = datetime.now(timezone.utc)
            try:
                data = fetch_feed(row["feed_url"])
                conn.execute(
                    "UPDATE feeds SET feed_title = %s, feed_icon_url = %s,"
                    " latest_post_title = %s, latest_post_url = %s,"
                    " last_updated = %s, last_fetched = %s"
                    " WHERE id = %s",
                    (
                        data["feed_title"],
                        data["feed_icon_url"],
                        data["latest_post_title"],
                        data["latest_post_url"],
                        data["last_updated"],
                        now,
                        row["id"],
                    ),
                )
                conn.commit()
            except Exception:
                logger.exception("Failed to fetch feed %s", row["feed_url"])
                conn.execute(
                    "UPDATE feeds SET last_fetched = %s WHERE id = %s",
                    (now, row["id"]),
                )
                conn.commit()
