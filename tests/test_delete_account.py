from app import app
from db import (
    create_post,
    create_user_and_site,
    get_site_by_subdomain,
    get_user_by_email,
    get_user_by_id,
)

HOST = {"Host": "myblog.jottit.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_delete_account_requires_auth(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get("/-/settings/delete-account", headers=HOST)
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_delete_account_rejects_wrong_confirmation(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/-/settings/delete-account",
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
        "/-/settings/delete-account",
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
        "/-/settings/delete-account",
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
        "/-/settings/delete-account",
        data={"confirmation": "delete"},
        headers=HOST,
    )
    response = client.get("/hello", headers=HOST)
    assert response.status_code == 404


def test_delete_account_with_multiple_sites(client):
    with app.app_context():
        user, site1 = create_user_and_site("owner@example.com", "myblog")
        _, site2 = create_user_and_site("owner@example.com", "second")
        create_post(site1["id"], "post1", "Post 1", "Body")
        create_post(site2["id"], "post2", "Post 2", "Body")
    login(client, user["id"])
    response = client.post(
        "/-/settings/delete-account",
        data={"confirmation": "delete"},
        headers=HOST,
    )
    assert response.status_code == 302

    with app.app_context():
        assert get_site_by_subdomain("myblog") is None
        assert get_site_by_subdomain("second") is None
        assert get_user_by_email("owner@example.com") is None

    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_delete_site_removes_only_that_site(client):
    with app.app_context():
        user, site1 = create_user_and_site("owner@example.com", "myblog")
        _, site2 = create_user_and_site("owner@example.com", "second")
        create_post(site1["id"], "post1", "Post 1", "Body")
        create_post(site2["id"], "post2", "Post 2", "Body")
    login(client, user["id"])
    response = client.post(
        "/-/settings/delete-site",
        data={"confirmation": "delete"},
        headers=HOST,
    )
    assert response.status_code == 302

    with app.app_context():
        assert get_site_by_subdomain("myblog") is None
        assert get_site_by_subdomain("second") is not None
        assert get_user_by_id(user["id"]) is not None


def test_delete_last_site_deletes_account(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/-/settings/delete-site",
        data={"confirmation": "delete"},
        headers=HOST,
    )
    assert response.status_code == 302

    with app.app_context():
        assert get_site_by_subdomain("myblog") is None
        assert get_user_by_email("owner@example.com") is None

    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_delete_account_page_lists_all_sites(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
        create_user_and_site("owner@example.com", "second")
    login(client, user["id"])
    response = client.get("/-/settings/delete-account", headers=HOST)
    assert response.status_code == 200
    assert b"myblog.jottit.pub" in response.data
    assert b"second.jottit.pub" in response.data
