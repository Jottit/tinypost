from unittest.mock import patch

from app import app
from auth import hash_passcode, verify_passcode
from db import create_user

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def setup_site(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    return user


# ── Passcode hashing ────────────────────


def test_hash_passcode_returns_hex():
    h = hash_passcode("123456")
    assert len(h) == 64
    assert h != "123456"


def test_verify_passcode_correct():
    h = hash_passcode("123456")
    assert verify_passcode("123456", h) is True


def test_verify_passcode_wrong():
    h = hash_passcode("123456")
    assert verify_passcode("000000", h) is False


# ── Signup validation ──────────


@patch("routes.auth.send_passcode")
def test_signup_rejects_invalid_subdomain(mock_send, client):
    with client.session_transaction() as sess:
        sess["signup"] = {
            "name": "Test",
            "email": "u@example.com",
            "passcode": "x",
            "verified": True,
        }
    response = client.post("/signup/address", data={"subdomain": "---"})
    assert response.status_code == 200
    assert b"Must be" in response.data
    mock_send.assert_not_called()


@patch("routes.auth.send_passcode")
def test_signup_sends_passcode_for_valid_email(mock_send, client):
    with client.session_transaction() as sess:
        sess["signup"] = {"name": "Test"}
    response = client.post("/signup/email/send", data={"email": "u@example.com"})
    assert response.status_code == 200
    mock_send.assert_called_once()


# ── IndieAuth redirect_uri validation ────


def test_indieauth_rejects_mismatched_redirect_uri(client):
    setup_site(client)
    resp = client.get(
        "/auth",
        query_string={
            "response_type": "code",
            "client_id": "https://example.com",
            "redirect_uri": "https://evil.com/callback",
            "code_challenge": "test",
        },
        base_url="http://myblog.tinypost.localhost:8000",
    )
    assert resp.status_code == 400


def test_indieauth_allows_matching_redirect_uri(client):
    setup_site(client)
    resp = client.get(
        "/auth",
        query_string={
            "response_type": "code",
            "client_id": "https://example.com",
            "redirect_uri": "https://example.com/callback",
            "code_challenge": "test",
        },
        base_url="http://myblog.tinypost.localhost:8000",
    )
    assert resp.status_code == 200
