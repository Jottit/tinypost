from app import app
from db import create_post, create_user_and_site, update_site

HOST = {"Host": "myblog.jottit.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_menu_visible_to_owner(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/", headers=HOST)
    assert b"admin-menu" in response.data
    assert b"> Write</button>" in response.data


def test_menu_not_visible_to_non_owner(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get("/", headers=HOST)
    assert b"admin-menu" not in response.data


def test_menu_not_visible_on_editor(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/edit", headers=HOST)
    assert b"admin-menu" not in response.data


def test_dropdown_links_present(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/", headers=HOST)
    assert b"/settings" in response.data
    assert b"/design" in response.data
    assert b"/account" in response.data
    assert b"/signout" in response.data


def test_menu_on_post_page(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Hello", "World")
    login(client, user["id"])
    response = client.get("/hello", headers=HOST)
    assert b"admin-menu" in response.data


def test_initials_from_single_word_title(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/", headers=HOST)
    assert b"admin-initials" in response.data


def test_initials_from_two_word_title(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site(site["id"], "Simon Carstensen", None)
    login(client, user["id"])
    response = client.get("/", headers=HOST)
    assert b"SC" in response.data
