from app import app
from db import create_post, create_user, update_user_blog

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_banner_visible_to_owner(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/", headers=HOST)
    assert b"admin-banner" in response.data
    assert b"/-/edit" in response.data


def test_banner_not_visible_to_non_owner(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.get("/", headers=HOST)
    assert b"admin-banner" not in response.data


def test_menu_not_visible_on_editor(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/edit", headers=HOST)
    assert b"admin-banner" not in response.data


def test_banner_links_present(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/", headers=HOST)
    assert b"/-/settings" in response.data
    assert b"/-/edit" in response.data


def test_banner_on_post_page(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        create_post(user["id"], "hello", "Hello", "World")
    login(client, user["id"])
    response = client.get("/hello", headers=HOST)
    assert b"admin-banner" in response.data


def test_initials_from_single_word_title(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/", headers=HOST)
    assert b"admin-initials" in response.data


def test_initials_from_two_word_title(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        update_user_blog(user["id"], "Simon Carstensen", None)
    login(client, user["id"])
    response = client.get("/", headers=HOST)
    assert b"SC" in response.data
