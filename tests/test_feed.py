import json
import xml.etree.ElementTree as ET

from app import app
from db import create_post, create_user_and_site

SITE_HOST = "myblog.tinypost.localhost:8000"


def _setup_site_with_posts(n=3):
    with app.app_context():
        _, site = create_user_and_site("owner@example.com", "myblog")
        for i in range(n):
            create_post(site["id"], f"post-{i}", f"Post {i}", f"Body of post {i}")


def test_rss_feed_content_type(client):
    _setup_site_with_posts()
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert "application/rss+xml" in response.content_type


def test_rss_feed_valid_xml(client):
    _setup_site_with_posts()
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    root = ET.fromstring(response.data)
    assert root.tag == "rss"
    assert root.attrib["version"] == "2.0"
    channel = root.find("channel")
    assert channel.find("title").text == "myblog"
    assert channel.find("link").text is not None


def test_rss_feed_items(client):
    _setup_site_with_posts()
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    root = ET.fromstring(response.data)
    channel = root.find("channel")
    items = channel.findall("item")
    assert len(items) == 3
    item = items[0]
    assert item.find("title").text is not None
    assert item.find("link").text is not None
    assert item.find("guid").text is not None
    assert item.find("pubDate").text is not None
    assert item.find("description").text is not None


def test_rss_feed_content_encoded(client):
    _setup_site_with_posts(1)
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    root = ET.fromstring(response.data)
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    items = root.find("channel").findall("item")
    encoded = items[0].find("content:encoded", ns)
    assert encoded is not None
    assert "<p>" in encoded.text


def test_rss_feed_source_markdown(client):
    _setup_site_with_posts(1)
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    root = ET.fromstring(response.data)
    ns = {"source": "http://source.scripting.com/"}
    items = root.find("channel").findall("item")
    markdown_el = items[0].find("source:markdown", ns)
    assert markdown_el is not None
    assert "Body of post 0" in markdown_el.text


def test_json_feed_content_type(client):
    _setup_site_with_posts()
    response = client.get("/feed.json", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert "application/feed+json" in response.content_type


def test_json_feed_structure(client):
    _setup_site_with_posts()
    response = client.get("/feed.json", headers={"Host": SITE_HOST})
    data = json.loads(response.data)
    assert data["version"] == "https://jsonfeed.org/version/1.1"
    assert data["title"] == "myblog"
    assert "home_page_url" in data
    assert "feed_url" in data
    assert len(data["items"]) == 3


def test_json_feed_items(client):
    _setup_site_with_posts(1)
    response = client.get("/feed.json", headers={"Host": SITE_HOST})
    data = json.loads(response.data)
    item = data["items"][0]
    assert "id" in item
    assert "url" in item
    assert "title" in item
    assert "content_html" in item
    assert "content_text" in item
    assert "date_published" in item
    assert "<p>" in item["content_html"]
    assert "Body of post 0" in item["content_text"]


def test_feed_404_for_nonexistent_site(client):
    response = client.get("/feed.xml", headers={"Host": "nosuchsite.tinypost.localhost:8000"})
    assert response.status_code == 404


def test_json_feed_404_for_nonexistent_site(client):
    response = client.get("/feed.json", headers={"Host": "nosuchsite.tinypost.localhost:8000"})
    assert response.status_code == 404


def test_autodiscovery_on_site_page(client):
    _setup_site_with_posts()
    response = client.get("/", headers={"Host": SITE_HOST})
    html = response.data.decode()
    assert 'type="application/rss+xml"' in html
    assert 'type="application/feed+json"' in html
    assert 'href="/feed.xml"' in html
    assert 'href="/feed.json"' in html


def test_autodiscovery_on_post_page(client):
    _setup_site_with_posts(1)
    response = client.get("/post-0", headers={"Host": SITE_HOST})
    html = response.data.decode()
    assert 'type="application/rss+xml"' in html
    assert 'type="application/feed+json"' in html
