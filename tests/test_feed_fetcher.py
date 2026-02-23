from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import feedparser as _feedparser
import pytest

from app import app
from db import create_user_and_site, get_blogroll, update_blogroll
from feed_fetcher import discover_feed_url, fetch_feed, refresh_all_feeds

HOST = {"Host": "myblog.jottit.localhost:8000"}

HTML_WITH_RSS = """<html><head>
<link rel="alternate" type="application/rss+xml" href="https://example.com/feed.xml">
</head><body></body></html>"""

HTML_WITH_ATOM = """<html><head>
<link rel="alternate" type="application/atom+xml" href="/atom.xml">
</head><body></body></html>"""

HTML_NO_FEED = """<html><head>
<link rel="stylesheet" href="/style.css">
</head><body></body></html>"""

HTML_RELATIVE_HREF = """<html><head>
<link rel="alternate" type="application/rss+xml" href="/blog/feed">
</head><body></body></html>"""

RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Blog</title>
    <item>
      <title>My Latest Post</title>
      <link>https://example.com/my-latest-post</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Blog</title>
  <entry>
    <title>Atom Post</title>
    <link href="https://example.com/atom-post"/>
    <updated>2024-01-15T10:00:00Z</updated>
  </entry>
</feed>"""

PARSED_RSS = _feedparser.parse(RSS_FEED)
PARSED_ATOM = _feedparser.parse(ATOM_FEED)

IMAGE_FEED_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Blog</title>
    <image><url>https://example.com/logo.png</url></image>
    <item><title>Post</title></item>
  </channel>
</rss>"""
PARSED_IMAGE_FEED = _feedparser.parse(IMAGE_FEED_XML)


@patch("feed_fetcher.urllib.request.urlopen")
def test_discover_feed_url_rss(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = HTML_WITH_RSS.encode()
    mock_urlopen.return_value = mock_resp

    result = discover_feed_url("https://example.com")
    assert result == "https://example.com/feed.xml"


@patch("feed_fetcher.urllib.request.urlopen")
def test_discover_feed_url_atom(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = HTML_WITH_ATOM.encode()
    mock_urlopen.return_value = mock_resp

    result = discover_feed_url("https://example.com")
    assert result == "https://example.com/atom.xml"


@patch("feed_fetcher.urllib.request.urlopen")
def test_discover_feed_url_no_feed(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = HTML_NO_FEED.encode()
    mock_urlopen.return_value = mock_resp

    result = discover_feed_url("https://example.com")
    assert result is None


@patch("feed_fetcher.urllib.request.urlopen")
def test_discover_feed_url_relative_href(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = HTML_RELATIVE_HREF.encode()
    mock_urlopen.return_value = mock_resp

    result = discover_feed_url("https://example.com")
    assert result == "https://example.com/blog/feed"


def test_discover_feed_url_network_error():
    result = discover_feed_url("https://nonexistent.invalid")
    assert result is None


def _setup():
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    return user, site


def _mock_favicon_response(mock_urlopen, content_type="image/x-icon"):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": content_type}
    mock_urlopen.return_value = mock_resp


@patch("feed_fetcher.urllib.request.urlopen")
@patch("feed_fetcher.feedparser.parse")
def test_fetch_feed_rss(mock_parse, mock_urlopen):
    mock_parse.return_value = PARSED_RSS
    _mock_favicon_response(mock_urlopen)

    result = fetch_feed("https://example.com/feed.xml")
    assert result["feed_title"] == "Test Blog"
    assert result["latest_post_title"] == "My Latest Post"
    assert result["latest_post_url"] == "https://example.com/my-latest-post"
    assert result["last_updated"] is not None
    assert result["feed_icon_url"] == "https://example.com/favicon.ico"


@patch("feed_fetcher.urllib.request.urlopen")
@patch("feed_fetcher.feedparser.parse")
def test_fetch_feed_atom(mock_parse, mock_urlopen):
    mock_parse.return_value = PARSED_ATOM
    _mock_favicon_response(mock_urlopen)

    result = fetch_feed("https://example.com/atom.xml")
    assert result["feed_title"] == "Atom Blog"
    assert result["latest_post_title"] == "Atom Post"
    assert result["latest_post_url"] == "https://example.com/atom-post"
    assert result["last_updated"] is not None


@patch("feed_fetcher.feedparser.parse")
def test_fetch_feed_parse_error(mock_parse):
    mock_result = MagicMock()
    mock_result.bozo = True
    mock_result.bozo_exception = Exception("bad xml")
    mock_result.entries = []
    mock_parse.return_value = mock_result

    with pytest.raises(ValueError):
        fetch_feed("https://example.com/bad.xml")


@patch("feed_fetcher.urllib.request.urlopen")
@patch("feed_fetcher.feedparser.parse")
def test_favicon_fallback_to_feed_image(mock_parse, mock_urlopen):
    mock_urlopen.side_effect = Exception("Connection refused")
    mock_parse.return_value = PARSED_IMAGE_FEED

    result = fetch_feed("https://example.com/feed.xml")
    assert result["feed_icon_url"] is None or "example.com" in result["feed_icon_url"]


@patch("feed_fetcher.urllib.request.urlopen")
@patch("feed_fetcher.feedparser.parse")
def test_favicon_head_non_image(mock_parse, mock_urlopen):
    _mock_favicon_response(mock_urlopen, content_type="text/html")
    mock_parse.return_value = PARSED_RSS

    result = fetch_feed("https://example.com/feed.xml")
    assert result["feed_icon_url"] is None


@patch("feed_fetcher.fetch_feed")
def test_refresh_all_feeds_updates_db(mock_fetch, client):
    _, site = _setup()

    with app.app_context():
        update_blogroll(
            site["id"],
            [
                {
                    "name": "Test Blog",
                    "url": "https://example.com",
                    "feed_url": "https://example.com/feed.xml",
                },
            ],
        )

    mock_fetch.return_value = {
        "feed_title": "Test Blog Title",
        "feed_icon_url": "https://example.com/favicon.ico",
        "latest_post_title": "Latest Post",
        "latest_post_url": "https://example.com/latest-post",
        "last_updated": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }

    refresh_all_feeds()

    with app.app_context():
        items = get_blogroll(site["id"])
        assert len(items) == 1
        assert items[0]["feed_title"] == "Test Blog Title"
        assert items[0]["latest_post_title"] == "Latest Post"
        assert items[0]["latest_post_url"] == "https://example.com/latest-post"
        assert items[0]["feed_icon_url"] == "https://example.com/favicon.ico"
        assert items[0]["last_fetched"] is not None


@patch("feed_fetcher.fetch_feed")
@patch("feed_fetcher.discover_feed_url")
def test_refresh_all_feeds_discovers_missing_feed_url(mock_discover, mock_fetch, client):
    _, site = _setup()

    with app.app_context():
        update_blogroll(
            site["id"],
            [{"name": "No Feed Blog", "url": "https://nofeed.example.com"}],
        )

    mock_discover.return_value = "https://nofeed.example.com/rss"
    mock_fetch.return_value = {
        "feed_title": "Discovered Blog",
        "feed_icon_url": None,
        "latest_post_title": "First Post",
        "latest_post_url": "https://nofeed.example.com/first-post",
        "last_updated": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }

    refresh_all_feeds()

    with app.app_context():
        items = get_blogroll(site["id"])
        assert items[0]["feed_url"] == "https://nofeed.example.com/rss"
        assert items[0]["feed_title"] == "Discovered Blog"


def test_sidebar_renders_feed_metadata(client):
    _, site = _setup()

    with app.app_context():
        update_blogroll(
            site["id"],
            [
                {
                    "name": "Cool Blog",
                    "url": "https://cool.example.com",
                    "feed_url": "https://cool.example.com/feed",
                },
            ],
        )
        from db import get_db

        db = get_db()
        db.execute(
            "UPDATE blogroll SET latest_post_title = %s, feed_icon_url = %s WHERE site_id = %s",
            ("A Great Post", "https://cool.example.com/favicon.ico", site["id"]),
        )
        db.commit()

    response = client.get("/", headers=HOST)
    assert response.status_code == 200
    assert b"Cool Blog" in response.data
    assert b"A Great Post" in response.data
    assert b"favicon.ico" in response.data


def test_sidebar_renders_initial_fallback(client):
    _, site = _setup()

    with app.app_context():
        update_blogroll(
            site["id"],
            [
                {"name": "No Icon Blog", "url": "https://noicon.example.com"},
            ],
        )

    response = client.get("/", headers=HOST)
    assert response.status_code == 200
    assert b"blogroll-icon-fallback" in response.data
    assert b">N<" in response.data


def test_sidebar_links_latest_post(client):
    _, site = _setup()

    with app.app_context():
        update_blogroll(
            site["id"],
            [
                {
                    "name": "Linked Blog",
                    "url": "https://linked.example.com",
                    "feed_url": "https://linked.example.com/feed",
                },
            ],
        )
        from db import get_db

        db = get_db()
        db.execute(
            "UPDATE blogroll SET latest_post_title = %s, latest_post_url = %s WHERE site_id = %s",
            ("Great Article", "https://linked.example.com/great-article", site["id"]),
        )
        db.commit()

    response = client.get("/", headers=HOST)
    assert response.status_code == 200
    assert b"https://linked.example.com/great-article" in response.data
    assert b"Great Article" in response.data


def test_sidebar_limits_to_five(client):
    _, site = _setup()

    with app.app_context():
        items = [{"name": f"Blog {i}", "url": f"https://blog{i}.example.com"} for i in range(8)]
        update_blogroll(site["id"], items)

    response = client.get("/", headers=HOST)
    assert response.status_code == 200
    assert b"Blog 0" in response.data
    assert b"Blog 4" in response.data
    assert b"Blog 5" not in response.data
    assert b"See all (8)" in response.data


def test_blogroll_page_public(client):
    _, site = _setup()

    with app.app_context():
        update_blogroll(
            site["id"],
            [
                {"name": "Public Blog", "url": "https://public.example.com"},
            ],
        )

    response = client.get("/blogroll", headers=HOST)
    assert response.status_code == 200
    assert b"Public Blog" in response.data
    assert b"Blogroll" in response.data


def test_timeago_filter():

    with app.app_context():
        env = app.jinja_env
        timeago = env.filters["timeago"]
        now = datetime.now(timezone.utc)
        assert timeago(None) == ""
        assert timeago(now) == "just now"
        assert timeago(now.replace(year=now.year - 2)) == "2y"
