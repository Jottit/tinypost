from app import app
from db import create_post, create_user
from tests.conftest import SITE_HOST


def _create_posts(n):
    with app.app_context():
        user = create_user("page@example.com", "myblog")
        for i in range(n):
            create_post(user["id"], f"post-{i}", f"Post {i}", f"Body {i}")
    return user


def test_page_1_shows_20_posts(client):
    _create_posts(25)
    resp = client.get("/", base_url=f"http://{SITE_HOST}")
    assert resp.status_code == 200
    assert resp.data.count(b"h-entry") == 20


def test_page_2_shows_remaining_posts(client):
    _create_posts(25)
    resp = client.get("/?page=2", base_url=f"http://{SITE_HOST}")
    assert resp.status_code == 200
    assert resp.data.count(b"h-entry") == 5


def test_older_link_on_page_1(client):
    _create_posts(25)
    resp = client.get("/", base_url=f"http://{SITE_HOST}")
    assert b"Older" in resp.data


def test_no_newer_link_on_page_1(client):
    _create_posts(25)
    resp = client.get("/", base_url=f"http://{SITE_HOST}")
    assert b"Newer" not in resp.data


def test_newer_link_on_page_2(client):
    _create_posts(25)
    resp = client.get("/?page=2", base_url=f"http://{SITE_HOST}")
    assert b"Newer" in resp.data


def test_no_older_link_on_last_page(client):
    _create_posts(25)
    resp = client.get("/?page=2", base_url=f"http://{SITE_HOST}")
    assert b"Older" not in resp.data


def test_no_pagination_when_few_posts(client):
    _create_posts(5)
    resp = client.get("/", base_url=f"http://{SITE_HOST}")
    assert b"Older" not in resp.data
    assert b"Newer" not in resp.data
