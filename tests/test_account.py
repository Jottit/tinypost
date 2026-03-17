from unittest.mock import patch

from app import app
from db import create_user, get_user_by_id

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_account_redirects_to_email(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user["id"])
    response = client.get("/-/account", headers=HOST)
    assert response.status_code == 302
    assert "/-/account/email" in response.headers["Location"]


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
