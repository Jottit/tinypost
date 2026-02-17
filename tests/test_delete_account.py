from app import app
from db import create_post, create_user_and_site, get_site_by_subdomain, get_user_by_email

HOST = {"Host": "myblog.jottit.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_delete_account_requires_auth(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get("/settings/delete-account", headers=HOST)
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_delete_account_rejects_wrong_confirmation(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/settings/delete-account",
        data={"confirmation": "nope"},
        headers=HOST,
    )
    assert response.status_code == 200
    assert b"Type" in response.data


def test_delete_account_success(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Hello", "World")
    login(client, user["id"])
    response = client.post(
        "/settings/delete-account",
        data={"confirmation": "delete"},
        headers=HOST,
    )
    assert response.status_code == 302

    with app.app_context():
        assert get_site_by_subdomain("myblog") is None
        assert get_user_by_email("owner@example.com") is None

    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_deleted_site_returns_404(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Hello", "World")
    login(client, user["id"])
    client.post(
        "/settings/delete-account",
        data={"confirmation": "delete"},
        headers=HOST,
    )
    response = client.get("/", headers=HOST)
    assert response.status_code == 404


def test_deleted_post_returns_404(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Hello", "World")
    login(client, user["id"])
    client.post(
        "/settings/delete-account",
        data={"confirmation": "delete"},
        headers=HOST,
    )
    response = client.get("/hello", headers=HOST)
    assert response.status_code == 404
