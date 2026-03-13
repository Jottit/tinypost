from unittest.mock import patch

from app import app
from db import create_post, create_user
from utils import RESERVED_SLUGS

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def setup_site(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    return user


# ── Signup checks subdomain_taken ────────


def test_signup_rejects_taken_subdomain(client):
    with app.app_context():
        create_user("taken@example.com", "taken")
    with client.session_transaction() as sess:
        sess["signup"] = {
            "name": "Test",
            "email": "new@example.com",
            "passcode": "x",
            "verified": True,
        }
    response = client.post("/signup/address", data={"subdomain": "taken"})
    assert response.status_code == 200
    assert b"not available" in response.data


# ── Reserved slug protection ─────────────


def test_reserved_slugs_not_empty():
    assert len(RESERVED_SLUGS) > 0
    assert "feed.xml" in RESERVED_SLUGS
    assert "signin" in RESERVED_SLUGS


def test_create_post_with_reserved_slug(client):
    setup_site(client)
    response = client.post(
        "/-/edit",
        data={"title": "Signin", "body": "Some content"},
        headers=HOST,
    )
    assert response.status_code == 200
    assert b"reserved" in response.data


# ── send_post marks sent before sending ──


@patch("routes.posts.send_email")
def test_send_post_marks_sent_before_emails(mock_send, client):
    user = setup_site(client)
    with app.app_context():
        create_post(user["id"], "hello", "Hello", "Body")
        from db import create_subscriber

        create_subscriber(user["id"], "sub@example.com", "tok-1")
        from db import confirm_subscriber

        confirm_subscriber("tok-1")

    def check_sent_at(*args, **kwargs):
        with app.app_context():
            from db import get_post_by_slug

            p = get_post_by_slug(user["id"], "hello")
            assert p["sent_at"] is not None

    mock_send.side_effect = check_sent_at
    client.post("/-/send/hello", headers=HOST)
    mock_send.assert_called_once()
