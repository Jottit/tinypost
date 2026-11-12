import json
import xml.etree.ElementTree as ET
from unittest.mock import patch

from app import app
from db import confirm_subscriber, create_post, create_subscriber, create_user

HOST = {"Host": "myblog.tinypost.localhost:8000"}

EVIL_BODY = """Hello there.

<script>alert('xss-script')</script>

<img src="/uploads/a.png" onerror="alert('xss-img')">

[click](javascript:alert)

<a href="javascript:alert('xss-raw-link')">raw</a>

<form action="https://evil.example/form"><input name="q"></form>

<iframe src="https://evil.example/frame"></iframe>
"""

MARKERS = ["xss-", "evil.example", "onerror", "javascript:", "<script>alert", "<iframe"]

GOOD_BODY = """## A heading

A [link](https://example.com "Example") and *emphasis* and **strong**.

![alt text](/uploads/pic.png)

    code block

- one
- two

Between lists.

1. first

> a quote
"""


def _setup(body):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        create_post(user["id"], "post", "Post", body)
    return user


def _assert_clean(text):
    for marker in MARKERS:
        assert marker not in text, marker


def _post_body_html(client):
    page = client.get("/post", headers=HOST).get_data(as_text=True)
    start = page.index('<div class="e-content post-body">')
    return page[start : page.index("</div>", start)]


def test_post_page_strips_dangerous_html(client):
    _setup(EVIL_BODY)
    html = _post_body_html(client)
    assert "Hello there." in html
    _assert_clean(html)


def test_home_page_strips_dangerous_html(client):
    _setup(EVIL_BODY)
    page = client.get("/", headers=HOST).get_data(as_text=True)
    assert "Hello there." in page
    _assert_clean(page)


def test_rss_feed_strips_dangerous_html(client):
    _setup(EVIL_BODY)
    root = ET.fromstring(client.get("/feed.xml", headers=HOST).data)
    item = root.find("channel/item")
    description = item.find("description").text
    encoded = item.find("{http://purl.org/rss/1.0/modules/content/}encoded").text
    assert "Hello there." in description
    _assert_clean(description)
    _assert_clean(encoded)


def test_json_feed_strips_dangerous_html(client):
    _setup(EVIL_BODY)
    data = json.loads(client.get("/feed.json", headers=HOST).data)
    content_html = data["items"][0]["content_html"]
    assert "Hello there." in content_html
    _assert_clean(content_html)


@patch("routes.posts.send_email")
def test_sent_email_strips_dangerous_html(mock_send, client):
    user = _setup(EVIL_BODY)
    with app.app_context():
        create_subscriber(user["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post("/-/send/post", headers=HOST)
    html = mock_send.call_args.kwargs["html"]
    assert "Hello there." in html
    _assert_clean(html)


def test_ordinary_markdown_still_renders(client):
    _setup(GOOD_BODY)
    html = _post_body_html(client)
    assert "<h2>A heading</h2>" in html
    assert (
        '<a href="https://example.com" title="Example" rel="noopener noreferrer">link</a>' in html
    )
    assert "<em>emphasis</em>" in html
    assert "<strong>strong</strong>" in html
    assert '<img alt="alt text" src="/uploads/pic.png">' in html
    assert "<pre><code>code block\n</code></pre>" in html
    assert "<ul>\n<li>one</li>" in html
    assert "<ol>\n<li>first</li>" in html
    assert "<blockquote>\n<p>a quote</p>\n</blockquote>" in html


def test_ordinary_markdown_in_feed(client):
    _setup(GOOD_BODY)
    data = json.loads(client.get("/feed.json", headers=HOST).data)
    content_html = data["items"][0]["content_html"]
    assert "<h2>A heading</h2>" in content_html
    assert '<img alt="alt text" src="/uploads/pic.png">' in content_html
