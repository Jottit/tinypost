from unittest.mock import patch

from app import app
from db import create_subscriber, create_user_and_site, get_subscriber, get_subscriber_by_token

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
        sub = create_subscriber(site["id"], "reader@example.com", "tok123")
        from db import confirm_subscriber

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
        sub = create_subscriber(site["id"], "reader@example.com", "confirmtok")
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
