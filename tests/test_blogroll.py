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


def test_blogroll_post_requires_auth(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.post(
        "/-/blogroll",
        data={"blogroll[0][name]": "Blog", "blogroll[0][url]": "https://example.com"},
        headers=HOST,
    )
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_blogroll_get(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/blogroll", headers=HOST)
    assert response.status_code == 200
    assert b"Blogroll" in response.data


def test_blogroll_post_saves_items(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/-/blogroll",
        data={
            "blogroll[0][name]": "Example Blog",
            "blogroll[0][url]": "https://example.com",
            "blogroll[1][name]": "Another Blog",
            "blogroll[1][url]": "https://another.com",
        },
        headers=HOST,
    )
    assert response.status_code == 302
    with app.app_context():
        items = get_blogroll(user["id"])
    assert len(items) == 2
    assert items[0]["name"] == "Example Blog"
    assert items[1]["name"] == "Another Blog"
