from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import feedparser as _feedparser

from app import app
from db import create_user_and_site, get_blogroll, update_blogroll

HOST = {"Host": "myblog.jottit.localhost:8000"}

RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Blog</title>
    <item>
      <title>My Latest Post</title>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Blog</title>
  <entry>
    <title>Atom Post</title>
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


def _setup():
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    return user, site


@patch("feed_fetcher.urllib.request.urlopen")
@patch("feed_fetcher.feedparser.parse")
def test_fetch_feed_rss(mock_parse, mock_urlopen):
    mock_parse.return_value = PARSED_RSS
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "image/x-icon"}
    mock_urlopen.return_value = mock_resp

    from feed_fetcher import fetch_feed

    result = fetch_feed("https://example.com/feed.xml")
    assert result["feed_title"] == "Test Blog"
    assert result["latest_post_title"] == "My Latest Post"
    assert result["last_updated"] is not None
    assert result["feed_icon_url"] == "https://example.com/favicon.ico"


@patch("feed_fetcher.urllib.request.urlopen")
@patch("feed_fetcher.feedparser.parse")
def test_fetch_feed_atom(mock_parse, mock_urlopen):
    mock_parse.return_value = PARSED_ATOM
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "image/x-icon"}
    mock_urlopen.return_value = mock_resp

    from feed_fetcher import fetch_feed

    result = fetch_feed("https://example.com/atom.xml")
    assert result["feed_title"] == "Atom Blog"
    assert result["latest_post_title"] == "Atom Post"
    assert result["last_updated"] is not None


@patch("feed_fetcher.feedparser.parse")
def test_fetch_feed_parse_error(mock_parse):
    mock_result = MagicMock()
    mock_result.bozo = True
    mock_result.bozo_exception = Exception("bad xml")
    mock_result.entries = []
    mock_parse.return_value = mock_result

    from feed_fetcher import fetch_feed

    try:
        fetch_feed("https://example.com/bad.xml")
        assert False, "Should have raised"
    except ValueError:
        pass


@patch("feed_fetcher.urllib.request.urlopen")
@patch("feed_fetcher.feedparser.parse")
def test_favicon_fallback_to_feed_image(mock_parse, mock_urlopen):
    mock_urlopen.side_effect = Exception("Connection refused")
    mock_parse.return_value = PARSED_IMAGE_FEED

    from feed_fetcher import fetch_feed

    result = fetch_feed("https://example.com/feed.xml")
    assert result["feed_icon_url"] is None or "example.com" in result["feed_icon_url"]


@patch("feed_fetcher.urllib.request.urlopen")
@patch("feed_fetcher.feedparser.parse")
def test_favicon_head_non_image(mock_parse, mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_urlopen.return_value = mock_resp
    mock_parse.return_value = PARSED_RSS

    from feed_fetcher import fetch_feed

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
        "last_updated": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }

    from feed_fetcher import refresh_all_feeds

    refresh_all_feeds()

    with app.app_context():
        items = get_blogroll(site["id"])
        assert len(items) == 1
        assert items[0]["feed_title"] == "Test Blog Title"
        assert items[0]["latest_post_title"] == "Latest Post"
        assert items[0]["feed_icon_url"] == "https://example.com/favicon.ico"
        assert items[0]["last_fetched"] is not None


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
        from models import get_db

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
