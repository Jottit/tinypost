from app import app
from db import create_user_and_site, get_user_by_id

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_account_requires_auth(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get("/-/account", headers=HOST)
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_account_shows_email(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/account", headers=HOST)
    assert response.status_code == 200
    assert b"owner@example.com" in response.data


def test_account_update_email(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/-/account",
        data={"email": "new@example.com"},
        headers=HOST,
    )
    assert response.status_code == 200
    assert b"Account updated" in response.data
    with app.app_context():
        updated = get_user_by_id(user["id"])
    assert updated["email"] == "new@example.com"


def test_account_email_required(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/-/account",
        data={"email": ""},
        headers=HOST,
    )
    assert response.status_code == 200
    assert b"Email is required" in response.data


def test_account_delete_link_present(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/account", headers=HOST)
    assert b"/-/settings/delete-account" in response.data
