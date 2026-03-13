from unittest.mock import patch

from app import app
from db import create_user, get_user_by_id

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_account_requires_auth(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.get("/-/account", headers=HOST)
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_account_shows_email_as_text_with_update_link(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/account", headers=HOST)
    assert response.status_code == 200
    assert b"owner@example.com" in response.data
    assert b"/-/account/email" in response.data
    assert b'name="email"' not in response.data


def test_account_post_only_updates_name(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    client.post(
        "/-/account",
        data={"name": "Alice"},
        headers=HOST,
    )
    with app.app_context():
        updated = get_user_by_id(user["id"])
    assert updated["name"] == "Alice"
    assert updated["email"] == "owner@example.com"


@patch("routes.account.send_passcode")
def test_account_update_email_with_passcode(mock_send, client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/-/account/email",
        data={"email": "new@example.com"},
        headers=HOST,
    )
    assert response.status_code == 200
    assert b"new@example.com" in response.data

    passcode = mock_send.call_args[0][1]

    response = client.post(
        "/-/account/email/verify",
        data={"passcode": passcode},
        headers=HOST,
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_user_by_id(user["id"])
    assert updated["email"] == "new@example.com"


def test_account_email_wrong_passcode(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    client.post(
        "/-/account/email",
        data={"email": "new@example.com"},
        headers=HOST,
    )
    response = client.post(
        "/-/account/email/verify",
        data={"passcode": "000000"},
        headers=HOST,
    )
    assert response.status_code == 200
    assert b"Invalid passcode" in response.data
    with app.app_context():
        updated = get_user_by_id(user["id"])
    assert updated["email"] == "owner@example.com"


def test_account_email_required(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.post(
        "/-/account/email",
        data={"email": ""},
        headers=HOST,
    )
    assert response.status_code == 200
    assert b"Email is required" in response.data


def test_account_page_has_token_section(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/account", headers=HOST)
    assert b"name" in response.data
    assert b"email" in response.data
    assert b"API token" in response.data
    assert b"/-/settings/delete-account" in response.data
