import json
import re
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

from app import app
from db import (
    create_auth_code,
    create_user,
    exchange_auth_code,
    get_subscriber,
    get_user_by_subdomain,
    set_custom_domain,
    set_user_plan,
    verify_custom_domain,
)
from tests.test_indieauth import pkce_pair

SITE = "http://myblog.tinypost.localhost:8000"


@pytest.fixture
def raw_client(client):
    """A client that does not add CSRF tokens on its own."""
    return FlaskClient(app, app.response_class, use_cookies=True)


@pytest.fixture
def owner(raw_client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with raw_client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["csrf_token"] = "right-token"
    return user


def title():
    with app.app_context():
        return get_user_by_subdomain("myblog")["title"]


def test_post_without_token_is_rejected(raw_client, owner):
    before = title()
    resp = raw_client.post("/-/settings/blog", data={"title": "Hacked"}, base_url=SITE)
    assert resp.status_code == 400
    assert title() == before


def test_post_with_wrong_token_is_rejected(raw_client, owner):
    before = title()
    resp = raw_client.post(
        "/-/settings/blog", data={"title": "Hacked", "csrf_token": "wrong"}, base_url=SITE
    )
    assert resp.status_code == 400
    assert title() == before


def test_delete_site_without_token_is_rejected(raw_client, owner):
    resp = raw_client.post(
        "/-/settings/delete-site", data={"confirmation": "delete"}, base_url=SITE
    )
    assert resp.status_code == 400
    with app.app_context():
        assert get_user_by_subdomain("myblog") is not None


def test_post_with_form_token_works(raw_client, owner):
    resp = raw_client.post(
        "/-/settings/blog", data={"title": "New", "csrf_token": "right-token"}, base_url=SITE
    )
    assert resp.status_code == 302
    assert title() == "New"


def test_post_with_header_token_works(raw_client, owner):
    resp = raw_client.post(
        "/-/settings/blog",
        data={"title": "New"},
        headers={"X-CSRF-Token": "right-token"},
        base_url=SITE,
    )
    assert resp.status_code == 302
    assert title() == "New"


def test_rendered_form_token_is_accepted(raw_client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    html = raw_client.get("/signin").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert f'<meta name="csrf-token" content="{token}">' in html
    with patch("routes.auth.send_passcode"):
        resp = raw_client.post("/signin", data={"email": "owner@example.com", "csrf_token": token})
    assert resp.status_code == 200


def test_micropub_needs_no_csrf_token(raw_client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        create_auth_code(
            user["id"],
            "code",
            "https://app.example.com",
            "https://app.example.com/cb",
            "create",
            "c",
            "S256",
        )
        exchange_auth_code("code", "access-token")
    resp = raw_client.post(
        "/micropub",
        data={"h": "entry", "content": "Hello"},
        headers={"Authorization": "Bearer access-token"},
        base_url=SITE,
    )
    assert resp.status_code == 201


def test_token_endpoint_needs_no_csrf_token(raw_client):
    verifier, challenge = pkce_pair()
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        create_auth_code(
            user["id"],
            "code",
            "https://example.com",
            "https://example.com/cb",
            "create",
            challenge,
            "S256",
        )
    resp = raw_client.post(
        "/auth/token",
        data={
            "grant_type": "authorization_code",
            "code": "code",
            "client_id": "https://example.com",
            "redirect_uri": "https://example.com/cb",
            "code_verifier": verifier,
        },
        base_url=SITE,
    )
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_stripe_webhook_needs_no_csrf_token(raw_client):
    event = {"type": "invoice.paid", "data": {"object": {"customer": "cus_none"}}}
    with (
        patch("routes.billing.STRIPE_SECRET_KEY", "sk_test"),
        patch("routes.billing.STRIPE_WEBHOOK_SECRET", "whsec_test"),
        patch("routes.billing.stripe.Webhook.construct_event", return_value=event),
    ):
        resp = raw_client.post(
            "/-/billing/webhook",
            data=json.dumps(event),
            content_type="application/json",
            headers={"Stripe-Signature": "t=1,v1=sig"},
        )
    assert resp.status_code == 200


def test_custom_domain_subscribe_needs_no_csrf_token(raw_client, monkeypatch):
    monkeypatch.setitem(app.config, "SERVER_NAME", None)
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        set_user_plan(user["id"], "yearly", "cus_test")
        set_custom_domain(user["id"], "example.com", "tok")
        verify_custom_domain(user["id"])
    with patch("routes.subscribers.send_email"):
        resp = raw_client.post(
            "/subscribe", data={"email": "reader@example.org"}, base_url="http://example.com"
        )
    assert resp.status_code == 200
    with app.app_context():
        assert get_subscriber(user["id"], "reader@example.org") is not None
