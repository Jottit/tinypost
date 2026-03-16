from app import app
from db import create_user, get_blogroll

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_blogroll_get_public(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.get("/blogroll", headers=HOST)
    assert response.status_code == 200


def test_blogroll_edit_redirects_to_following(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/blogroll", headers=HOST)
    assert response.status_code == 301
    assert "/-/following" in response.headers["Location"]


def test_following_get(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/following", headers=HOST)
    assert response.status_code == 200
    assert b"Following" in response.data


def test_following_add(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/-/following/add",
        data={"url": "https://example.com"},
        headers=HOST,
    )
    assert response.status_code == 302
    with app.app_context():
        items = get_blogroll(user["id"])
    assert len(items) == 1
    assert items[0]["url"] == "https://example.com"


def test_following_remove(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    client.post(
        "/-/following/add",
        data={"url": "https://example.com"},
        headers=HOST,
    )
    client.post(
        "/-/following/add",
        data={"url": "https://another.com"},
        headers=HOST,
    )
    response = client.post(
        "/-/following/remove",
        data={"url": "https://example.com"},
        headers=HOST,
    )
    assert response.status_code == 302
    with app.app_context():
        items = get_blogroll(user["id"])
    assert len(items) == 1
    assert items[0]["url"] == "https://another.com"


def test_following_add_requires_auth(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.post(
        "/-/following/add",
        data={"url": "https://example.com"},
        headers=HOST,
    )
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]
