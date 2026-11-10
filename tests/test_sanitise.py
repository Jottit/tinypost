import json
import xml.etree.ElementTree as ET
from unittest.mock import patch

from app import app
from db import confirm_subscriber, create_post, create_subscriber, create_user
from routes.feeds import CONTENT_NS
from utils import render_markdown

HEADERS = {"Host": "myblog.tinypost.localhost:8000"}

MALICIOUS_BODY = """Hello world

<script>alert('xss')</script>

<img src="x.png" onerror="alert('img')">

[click me](javascript:alert('link'))

<a href="javascript:alert('raw')">raw link</a>

<form action="https://evil.example/steal"><input name="pw"></form>

<iframe src="https://evil.example/"></iframe>
"""

DANGEROUS = [
    "<script>alert",
    "onerror",
    'href="javascript',
    'action="https://evil.example',
    'name="pw"',
    "<iframe",
]


def assert_clean(html):
    for needle in DANGEROUS:
        assert needle not in html, f"{needle!r} found in output"


def setup_post(body=MALICIOUS_BODY):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        create_post(user["id"], "hello", "Hello", body)
    return user


def test_render_markdown_strips_dangerous_html():
    html = render_markdown(MALICIOUS_BODY)
    assert_clean(html)
    assert "Hello world" in html


def test_render_markdown_keeps_ordinary_markdown():
    body = """# Heading

Some *emphasis*, **strong** and `code`.

[a link](https://example.com "Title") and [mail](mailto:a@example.com)

![alt text](/uploads/photo.jpg)

    indented code

- one
- two

Between lists.

1. first

> quoted

---
"""
    html = render_markdown(body)
    assert "<h1>Heading</h1>" in html
    assert "<em>emphasis</em>" in html
    assert "<strong>strong</strong>" in html
    assert "<code>code</code>" in html
    assert 'href="https://example.com"' in html
    assert 'title="Title"' in html
    assert 'rel="noopener noreferrer"' in html
    assert 'href="mailto:a@example.com"' in html
    assert '<img alt="alt text" src="/uploads/photo.jpg">' in html
    assert "<pre><code>" in html
    assert "indented code" in html
    assert "<ul>" in html and "<li>one</li>" in html
    assert "<ol>" in html and "<li>first</li>" in html
    assert "<blockquote>" in html
    assert "<hr>" in html


def test_post_page_strips_dangerous_html(client):
    setup_post()
    response = client.get("/hello", headers=HEADERS)
    assert response.status_code == 200
    assert_clean(response.data.decode())
    assert "Hello world" in response.data.decode()


def test_home_page_strips_dangerous_html(client):
    setup_post()
    response = client.get("/", headers=HEADERS)
    assert response.status_code == 200
    html = response.data.decode()
    assert "Hello world" in html
    assert_clean(html)


def test_rss_feed_strips_dangerous_html(client):
    setup_post()
    response = client.get("/feed.xml", headers=HEADERS)
    item = ET.fromstring(response.data).find("channel/item")
    for tag in ["description", f"{{{CONTENT_NS}}}encoded"]:
        html = item.find(tag).text
        assert "Hello world" in html
        assert_clean(html)
        assert "<script" not in html
        assert "<form" not in html


def test_json_feed_strips_dangerous_html(client):
    setup_post()
    response = client.get("/feed.json", headers=HEADERS)
    data = json.loads(response.data)
    html = data["items"][0]["content_html"]
    assert "Hello world" in html
    assert_clean(html)


@patch("routes.posts.send_email")
def test_sent_email_strips_dangerous_html(mock_send, client):
    user = setup_post()
    with app.app_context():
        create_subscriber(user["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post("/-/send/hello", headers=HEADERS)
    html = mock_send.call_args.kwargs["html"]
    assert "Hello world" in html
    assert_clean(html)
