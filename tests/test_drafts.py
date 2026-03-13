import json
import xml.etree.ElementTree as ET

from app import app
from db import create_post, create_user

SITE_HOST = "myblog.tinypost.localhost:8000"


def _setup_site():
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    return user


def test_draft_not_visible_on_public_site_page(client):
    user = _setup_site()
    with app.app_context():
        create_post(user["id"], "my-draft", "My Draft", "Draft body", is_draft=True)
    response = client.get("/", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"My Draft" not in response.data


def test_draft_visible_to_owner_on_site_page(client):
    user = _setup_site()
    with app.app_context():
        create_post(user["id"], "my-draft", "My Draft", "Draft body", is_draft=True)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"My Draft" in response.data
    assert b"Draft" in response.data


def test_draft_not_in_rss_feed(client):
    user = _setup_site()
    with app.app_context():
        create_post(user["id"], "my-draft", "My Draft", "Draft body", is_draft=True)
        create_post(user["id"], "published", "Published", "Published body")
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    root = ET.fromstring(response.data)
    items = root.find("channel").findall("item")
    titles = [item.find("title").text for item in items]
    assert "My Draft" not in titles
    assert "Published" in titles


def test_draft_not_in_json_feed(client):
    user = _setup_site()
    with app.app_context():
        create_post(user["id"], "my-draft", "My Draft", "Draft body", is_draft=True)
        create_post(user["id"], "published", "Published", "Published body")
    response = client.get("/feed.json", headers={"Host": SITE_HOST})
    data = json.loads(response.data)
    titles = [item["title"] for item in data["items"]]
    assert "My Draft" not in titles
    assert "Published" in titles


def test_draft_post_404_for_public_visitor(client):
    user = _setup_site()
    with app.app_context():
        create_post(user["id"], "my-draft", "My Draft", "Draft body", is_draft=True)
    response = client.get("/my-draft", headers={"Host": SITE_HOST})
    assert response.status_code == 404


def test_draft_post_200_for_owner(client):
    user = _setup_site()
    with app.app_context():
        create_post(user["id"], "my-draft", "My Draft", "Draft body", is_draft=True)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/my-draft", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"My Draft" in response.data
    assert b"Draft" in response.data


def test_toggle_draft_on_hides_from_public(client):
    user = _setup_site()
    with app.app_context():
        create_post(user["id"], "my-post", "My Post", "Post body")
    # Verify visible publicly
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"My Post" in response.data
    # Toggle to draft
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post(
        "/-/edit/my-post",
        data={"title": "My Post", "body": "Post body", "is_draft": "on"},
        headers={"Host": SITE_HOST},
    )
    # Clear session to view as public
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"My Post" not in response.data


def test_toggle_draft_off_shows_in_public(client):
    user = _setup_site()
    with app.app_context():
        create_post(user["id"], "my-post", "My Post", "Post body", is_draft=True)
    # Verify hidden publicly
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"My Post" not in response.data
    # Toggle off draft
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post(
        "/-/edit/my-post",
        data={"title": "My Post", "body": "Post body"},
        headers={"Host": SITE_HOST},
    )
    # Clear session to view as public
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"My Post" in response.data


def test_new_post_defaults_to_published(client):
    user = _setup_site()
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/-/edit", headers={"Host": SITE_HOST})
    html = response.data.decode()
    assert 'name="is_draft"' in html
    assert "checked" not in html.split('name="is_draft"')[1].split(">")[0]
