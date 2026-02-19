from unittest.mock import patch

from app import app
from db import (
    confirm_subscriber,
    create_post,
    create_subscriber,
    create_user_and_site,
    get_post_by_slug,
    get_subscriber,
    get_subscriber_by_token,
)

HEADERS = {"Host": "myblog.jottit.localhost:8000"}


def setup_site(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    return user, site


@patch("routes.send_email")
def test_subscribe(mock_send, client):
    setup_site(client)
    response = client.post("/subscribe", data={"email": "reader@example.com"}, headers=HEADERS)
    assert response.status_code == 200
    assert b"almost done" in response.data.lower()
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["to"] == "reader@example.com"
    assert "confirm" in mock_send.call_args.kwargs["subject"].lower()
    assert mock_send.call_args.kwargs["html"] is not None
    assert "confirm-subscriber@jottit.pub" in mock_send.call_args.kwargs["from_addr"]


@patch("routes.send_email")
def test_subscribe_creates_subscriber(mock_send, client):
    _, site = setup_site(client)
    client.post("/subscribe", data={"email": "reader@example.com"}, headers=HEADERS)
    with app.app_context():
        sub = get_subscriber(site["id"], "reader@example.com")
    assert sub is not None
    assert sub["confirmed"] is False


@patch("routes.send_email")
def test_subscribe_duplicate_resends_confirmation(mock_send, client):
    _, site = setup_site(client)
    client.post("/subscribe", data={"email": "reader@example.com"}, headers=HEADERS)
    client.post("/subscribe", data={"email": "reader@example.com"}, headers=HEADERS)
    assert mock_send.call_count == 2


@patch("routes.send_email")
def test_subscribe_already_confirmed_no_email(mock_send, client):
    _, site = setup_site(client)
    with app.app_context():
        create_subscriber(site["id"], "reader@example.com", "tok123")
        confirm_subscriber("tok123")
    response = client.post("/subscribe", data={"email": "reader@example.com"}, headers=HEADERS)
    assert response.status_code == 200
    mock_send.assert_not_called()


@patch("routes.send_email")
def test_honeypot_rejects(mock_send, client):
    setup_site(client)
    response = client.post(
        "/subscribe",
        data={"email": "bot@example.com", "website": "http://spam.com"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    mock_send.assert_not_called()


@patch("routes.send_email")
def test_confirm_subscription(mock_send, client):
    _, site = setup_site(client)
    with app.app_context():
        create_subscriber(site["id"], "reader@example.com", "confirmtok")
    response = client.get("/confirm/confirmtok", headers=HEADERS)
    assert response.status_code == 200
    assert b"on the list" in response.data.lower()
    assert b"unsubscribe/confirmtok" in response.data
    with app.app_context():
        sub = get_subscriber_by_token("confirmtok")
    assert sub["confirmed"] is True


def test_confirm_invalid_token(client):
    setup_site(client)
    response = client.get("/confirm/badtoken", headers=HEADERS)
    assert response.status_code == 404


@patch("routes.send_email")
def test_unsubscribe(mock_send, client):
    _, site = setup_site(client)
    with app.app_context():
        create_subscriber(site["id"], "reader@example.com", "unsub-tok")
    response = client.get("/unsubscribe/unsub-tok", headers=HEADERS)
    assert response.status_code == 200
    assert b"unsubscribed" in response.data.lower()
    with app.app_context():
        sub = get_subscriber_by_token("unsub-tok")
    assert sub is None


def test_unsubscribe_invalid_token(client):
    setup_site(client)
    response = client.get("/unsubscribe/badtoken", headers=HEADERS)
    assert response.status_code == 404


# ── Phase 2: Send to subscribers ─────────────────


@patch("routes.send_email")
def test_send_post_to_subscribers(mock_send, client):
    user, site = setup_site(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Post body here")
        create_subscriber(site["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
        create_subscriber(site["id"], "b@example.com", "tok-b")
        confirm_subscriber("tok-b")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post("/send/hello", headers=HEADERS)
    assert response.status_code == 302
    assert mock_send.call_count == 2
    recipients = {call.kwargs["to"] for call in mock_send.call_args_list}
    assert recipients == {"a@example.com", "b@example.com"}


@patch("routes.send_email")
def test_send_skips_unconfirmed(mock_send, client):
    user, site = setup_site(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
        create_subscriber(site["id"], "confirmed@example.com", "tok-c")
        confirm_subscriber("tok-c")
        create_subscriber(site["id"], "unconfirmed@example.com", "tok-u")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post("/send/hello", headers=HEADERS)
    assert mock_send.call_count == 1
    assert mock_send.call_args.kwargs["to"] == "confirmed@example.com"


@patch("routes.send_email")
def test_send_marks_post_sent(mock_send, client):
    user, site = setup_site(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
        create_subscriber(site["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post("/send/hello", headers=HEADERS)
    with app.app_context():
        post = get_post_by_slug(site["id"], "hello")
    assert post["sent_at"] is not None


@patch("routes.send_email")
def test_send_prevents_double_send(mock_send, client):
    user, site = setup_site(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
        create_subscriber(site["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post("/send/hello", headers=HEADERS)
    mock_send.reset_mock()
    client.post("/send/hello", headers=HEADERS)
    mock_send.assert_not_called()


@patch("routes.send_email")
def test_send_draft_not_allowed(mock_send, client):
    user, site = setup_site(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body", is_draft=True)
        create_subscriber(site["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post("/send/hello", headers=HEADERS)
    assert response.status_code == 302
    mock_send.assert_not_called()


def test_send_requires_auth(client):
    setup_site(client)
    with app.app_context():
        from db import get_site_by_subdomain

        site = get_site_by_subdomain("myblog")
        create_post(site["id"], "hello", "Hello", "Body")
    response = client.post("/send/hello", headers=HEADERS)
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_subscriber_count_hidden_for_visitors(client):
    _, site = setup_site(client)
    with app.app_context():
        create_subscriber(site["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
    response = client.get("/", headers=HEADERS)
    assert b"subscriber" not in response.data


def test_send_button_shown_on_edit(client):
    user, site = setup_site(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
        create_subscriber(site["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/edit/hello", headers=HEADERS)
    assert b"Send to 1 subscriber" in response.data


def test_send_button_hidden_for_draft(client):
    user, site = setup_site(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body", is_draft=True)
        create_subscriber(site["id"], "a@example.com", "tok-a")
        confirm_subscriber("tok-a")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/edit/hello", headers=HEADERS)
    assert b"Send to" not in response.data
