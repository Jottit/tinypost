from unittest.mock import patch

from app import app
from db import (
    create_comment,
    create_post,
    create_user_and_site,
    get_comment_by_id,
    get_db,
    get_site_by_id,
)

HEADERS = {"Host": "myblog.tinypost.localhost:8000"}


def setup_site_and_post(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        db = get_db()
        db.execute("UPDATE sites SET comments_enabled = TRUE WHERE id = %s", (site["id"],))
        db.commit()
        site = get_site_by_id(site["id"])
        post = create_post(site["id"], "hello", "Hello", "Post body here")
    return user, site, post


@patch("routes.comments.send_email")
def test_logged_in_user_can_comment(mock_send, client):
    user, site, post = setup_site_and_post(client)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/-/comment/hello",
        data={"name": "Owner", "body": "Nice post!"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    json = response.get_json()
    assert json["status"] == "ok"
    assert "comment_id" in json


@patch("routes.comments.send_email")
def test_logged_in_comment_appears_on_post(mock_send, client):
    user, site, post = setup_site_and_post(client)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post(
        "/-/comment/hello",
        data={"name": "Owner", "body": "Great stuff"},
        headers=HEADERS,
    )
    response = client.get("/hello", headers=HEADERS)
    assert b"Great stuff" in response.data
    assert b"Owner" in response.data


@patch("routes.comments.send_email")
def test_anonymous_comment_requires_verification(mock_send, client):
    setup_site_and_post(client)
    response = client.post(
        "/-/comment/hello",
        data={"name": "Reader", "email": "reader@example.com", "body": "Hello!"},
        headers=HEADERS,
    )
    json = response.get_json()
    assert json["status"] == "verify"
    assert "re****@example.com" in json["email"]


@patch("routes.comments.send_email")
@patch("routes.comments.send_passcode")
def test_anonymous_comment_passcode_flow(mock_passcode, mock_send, client):
    setup_site_and_post(client)
    client.post(
        "/-/comment/hello",
        data={"name": "Reader", "email": "reader@example.com", "body": "Hello!"},
        headers=HEADERS,
    )
    passcode = mock_passcode.call_args[0][1]
    response = client.post(
        "/-/comment/hello/verify",
        data={"passcode": passcode},
        headers=HEADERS,
    )
    json = response.get_json()
    assert json["status"] == "ok"
    assert "comment_id" in json
    # Notification sent to owner
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["to"] == "owner@example.com"


@patch("routes.comments.send_email")
@patch("routes.comments.send_passcode")
def test_wrong_passcode_rejected(mock_passcode, mock_send, client):
    setup_site_and_post(client)
    client.post(
        "/-/comment/hello",
        data={"name": "Reader", "email": "reader@example.com", "body": "Hello!"},
        headers=HEADERS,
    )
    response = client.post(
        "/-/comment/hello/verify",
        data={"passcode": "000000"},
        headers=HEADERS,
    )
    json = response.get_json()
    assert json["status"] == "error"
    assert "Wrong passcode" in json["message"]


def test_owner_can_delete_comment(client):
    user, site, post = setup_site_and_post(client)
    with app.app_context():
        comment = create_comment(post["id"], site["id"], "Someone", "abc123", "Spam")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        f"/-/comment/{comment['id']}/delete",
        headers=HEADERS,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_comment_by_id(comment["id"]) is None


def test_empty_body_rejected(client):
    setup_site_and_post(client)
    response = client.post(
        "/-/comment/hello",
        data={"name": "Reader", "email": "reader@example.com", "body": ""},
        headers=HEADERS,
    )
    assert response.status_code == 400
    json = response.get_json()
    assert json["status"] == "error"


def test_empty_name_rejected(client):
    setup_site_and_post(client)
    response = client.post(
        "/-/comment/hello",
        data={"name": "", "email": "reader@example.com", "body": "Hello!"},
        headers=HEADERS,
    )
    assert response.status_code == 400
    json = response.get_json()
    assert json["status"] == "error"


def test_honeypot_silently_ignored(client):
    setup_site_and_post(client)
    response = client.post(
        "/-/comment/hello",
        data={
            "name": "Bot",
            "email": "bot@example.com",
            "body": "Buy stuff!",
            "website": "http://spam.com",
        },
        headers=HEADERS,
    )
    json = response.get_json()
    assert json["status"] == "ok"


@patch("routes.comments.send_email")
def test_notification_sent_to_owner(mock_send, client):
    user, site, post = setup_site_and_post(client)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post(
        "/-/comment/hello",
        data={"name": "Owner", "body": "My comment"},
        headers=HEADERS,
    )
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["to"] == "owner@example.com"
    assert "New comment" in mock_send.call_args.kwargs["subject"]


def test_comment_count_shown_on_post(client):
    user, site, post = setup_site_and_post(client)
    with app.app_context():
        create_comment(post["id"], site["id"], "A", "hash1", "First")
        create_comment(post["id"], site["id"], "B", "hash2", "Second")
    response = client.get("/hello", headers=HEADERS)
    assert b"Comments (2)" in response.data
