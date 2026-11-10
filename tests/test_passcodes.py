from unittest.mock import patch

from app import app
from auth import hash_passcode
from db import create_user, get_db, get_user_by_id

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def _session_payload(response):
    header = next(h for h in response.headers.getlist("Set-Cookie") if h.startswith("session="))
    value = header.split(";")[0].removeprefix("session=")
    return str(app.session_interface.get_signing_serializer(app).loads(value))


def _expire_passcodes():
    with app.app_context():
        db = get_db()
        db.execute("UPDATE passcodes SET expires_at = NOW() - INTERVAL '1 minute'")
        db.commit()


def _start_signin(client):
    with patch("routes.auth.send_passcode") as mock_send:
        response = client.post("/signin", data={"email": "owner@example.com"})
    return mock_send.call_args[0][1], response


def _signed_in(client, user):
    with client.session_transaction() as sess:
        return sess.get("user_id") == user["id"]


# ── Session never holds the passcode ──────


def test_signin_session_has_no_passcode(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    passcode, response = _start_signin(client)
    payload = _session_payload(response)
    assert passcode not in payload
    assert hash_passcode(passcode) not in payload


@patch("routes.auth.send_passcode")
def test_signup_session_has_no_passcode(mock_send, client):
    response = client.post("/signup/email/send", data={"email": "u@example.com"})
    passcode = mock_send.call_args[0][1]
    payload = _session_payload(response)
    assert passcode not in payload
    assert hash_passcode(passcode) not in payload


@patch("routes.account.send_passcode")
def test_email_change_session_has_no_passcode(mock_send, client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post("/-/account/email", data={"email": "new@example.com"}, headers=HOST)
    passcode = mock_send.call_args[0][1]
    payload = _session_payload(response)
    assert passcode not in payload
    assert hash_passcode(passcode) not in payload


# ── Verification rules ────────────────────


def test_signin_correct_code(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    passcode, _ = _start_signin(client)
    response = client.post("/signin/verify", data={"passcode": passcode})
    assert response.status_code == 302
    assert _signed_in(client, user)


def test_signin_wrong_code(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    passcode, _ = _start_signin(client)
    wrong = "000000" if passcode != "000000" else "111111"
    response = client.post("/signin/verify", data={"passcode": wrong})
    assert b"Wrong passcode" in response.data
    assert not _signed_in(client, user)


def test_signin_expired_code(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    passcode, _ = _start_signin(client)
    _expire_passcodes()
    response = client.post("/signin/verify", data={"passcode": passcode})
    assert response.status_code == 200
    assert not _signed_in(client, user)


def test_signin_locked_after_five_wrong_attempts(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    passcode, _ = _start_signin(client)
    wrong = "000000" if passcode != "000000" else "111111"
    for _ in range(5):
        client.post("/signin/verify", data={"passcode": wrong})
    response = client.post("/signin/verify", data={"passcode": passcode})
    assert response.status_code == 200
    assert not _signed_in(client, user)


def test_signin_code_cannot_be_reused(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    passcode, _ = _start_signin(client)
    client.post("/signin/verify", data={"passcode": passcode})
    client.post("/signout")
    with client.session_transaction() as sess:
        sess["signin"] = {"email": "owner@example.com"}
    response = client.post("/signin/verify", data={"passcode": passcode})
    assert response.status_code == 200
    assert not _signed_in(client, user)


def test_signin_new_code_replaces_old(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    first, _ = _start_signin(client)
    second, _ = _start_signin(client)
    if first != second:
        response = client.post("/signin/verify", data={"passcode": first})
        assert not _signed_in(client, user)
    response = client.post("/signin/verify", data={"passcode": second})
    assert response.status_code == 302
    assert _signed_in(client, user)


@patch("routes.auth.send_passcode")
def test_signup_expired_code(mock_send, client):
    client.post("/signup/email/send", data={"email": "u@example.com"})
    passcode = mock_send.call_args[0][1]
    _expire_passcodes()
    response = client.post("/signup/verify", data={"passcode": passcode})
    assert b"Wrong passcode" in response.data


@patch("routes.account.send_passcode")
def test_email_change_code_tied_to_user(mock_send, client):
    with app.app_context():
        owner = create_user("owner@example.com", "myblog")
        other = create_user("other@example.com", "otherblog")
    with client.session_transaction() as sess:
        sess["user_id"] = other["id"]
    client.post(
        "/-/account/email",
        data={"email": "new@example.com"},
        headers={"Host": "otherblog.tinypost.localhost:8000"},
    )
    passcode = mock_send.call_args[0][1]
    with client.session_transaction() as sess:
        sess["user_id"] = owner["id"]
        sess["email_change"] = {"email": "new@example.com"}
    response = client.post("/-/account/email/verify", data={"passcode": passcode}, headers=HOST)
    assert b"Invalid passcode" in response.data
    with app.app_context():
        assert get_user_by_id(owner["id"])["email"] == "owner@example.com"
