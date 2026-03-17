import json
from unittest.mock import MagicMock, patch

from app import app
from db import create_user, get_user_by_id, set_user_paid

SITE_HOST = "myblog.tinypost.localhost:8000"


def _setup_site():
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    return user


def test_domain_page_shows_upgrade_for_free_user(client):
    user = _setup_site()
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/-/settings/domain", headers={"Host": SITE_HOST})
    assert b"Yearly" in response.data
    assert b"Monthly" in response.data
    assert b"$48 / year" in response.data
    assert b"$5 / month" in response.data
    assert b"2 months free" in response.data
    assert b"Continue with yearly" in response.data


def test_domain_page_shows_form_for_paid_user(client):
    user = _setup_site()
    with app.app_context():
        set_user_paid(user["id"], "cus_123")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/-/settings/domain", headers={"Host": SITE_HOST})
    assert b"Continue with yearly" not in response.data
    assert b'placeholder="yourname.com"' in response.data


def test_checkout_redirects_to_stripe(client):
    user = _setup_site()
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test"

    with patch("routes.billing.STRIPE_SECRET_KEY", "sk_test"), patch(
        "routes.billing.PRICE_IDS", {"month": "price_month", "year": "price_year"}
    ), patch(
        "routes.billing.stripe.checkout.Session.create", return_value=mock_session
    ) as mock_create:
        response = client.post(
            "/-/billing/checkout",
            data={"interval": "month"},
            headers={"Host": SITE_HOST},
        )
    assert response.status_code == 302
    assert "checkout.stripe.com" in response.headers["Location"]
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["line_items"][0]["price"] == "price_month"


def test_checkout_yearly(client):
    user = _setup_site()
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test"

    with patch("routes.billing.STRIPE_SECRET_KEY", "sk_test"), patch(
        "routes.billing.PRICE_IDS", {"month": "price_month", "year": "price_year"}
    ), patch(
        "routes.billing.stripe.checkout.Session.create", return_value=mock_session
    ) as mock_create:
        response = client.post(
            "/-/billing/checkout",
            data={"interval": "year"},
            headers={"Host": SITE_HOST},
        )
    assert mock_create.call_args.kwargs["line_items"][0]["price"] == "price_year"


def test_checkout_requires_login(client):
    response = client.post(
        "/-/billing/checkout",
        data={"interval": "month"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_webhook_checkout_completed(client):
    user = _setup_site()
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": str(user["id"])},
                "customer": "cus_abc123",
            }
        },
    }

    with patch("routes.billing.STRIPE_SECRET_KEY", "sk_test"), patch(
        "routes.billing.STRIPE_WEBHOOK_SECRET", "whsec_test"
    ), patch("routes.billing.stripe.Webhook.construct_event", return_value=event):
        response = client.post(
            "/-/billing/webhook",
            data=json.dumps(event),
            content_type="application/json",
            headers={"Stripe-Signature": "t=1,v1=sig"},
        )

    assert response.status_code == 200
    with app.app_context():
        updated = get_user_by_id(user["id"])
    assert updated["plan"] == "paid"
    assert updated["stripe_customer_id"] == "cus_abc123"


def test_webhook_subscription_deleted(client):
    user = _setup_site()
    with app.app_context():
        set_user_paid(user["id"], "cus_abc123")

    event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "customer": "cus_abc123",
            }
        },
    }

    with patch("routes.billing.STRIPE_SECRET_KEY", "sk_test"), patch(
        "routes.billing.STRIPE_WEBHOOK_SECRET", "whsec_test"
    ), patch("routes.billing.stripe.Webhook.construct_event", return_value=event):
        response = client.post(
            "/-/billing/webhook",
            data=json.dumps(event),
            content_type="application/json",
            headers={"Stripe-Signature": "t=1,v1=sig"},
        )

    assert response.status_code == 200
    with app.app_context():
        updated = get_user_by_id(user["id"])
    assert updated["plan"] == "free"
    assert updated["plan_expires_at"] is None


def test_webhook_invoice_paid(client):
    user = _setup_site()
    with app.app_context():
        set_user_paid(user["id"], "cus_abc123")

    event = {
        "type": "invoice.paid",
        "data": {
            "object": {
                "customer": "cus_abc123",
                "lines": {"data": [{"period": {"end": 1743724800}}]},
            }
        },
    }

    with patch("routes.billing.STRIPE_SECRET_KEY", "sk_test"), patch(
        "routes.billing.STRIPE_WEBHOOK_SECRET", "whsec_test"
    ), patch("routes.billing.stripe.Webhook.construct_event", return_value=event):
        response = client.post(
            "/-/billing/webhook",
            data=json.dumps(event),
            content_type="application/json",
            headers={"Stripe-Signature": "t=1,v1=sig"},
        )

    assert response.status_code == 200
    with app.app_context():
        updated = get_user_by_id(user["id"])
    assert updated["plan_expires_at"] is not None


def test_webhook_invalid_signature(client):
    with patch("routes.billing.STRIPE_SECRET_KEY", "sk_test"), patch(
        "routes.billing.STRIPE_WEBHOOK_SECRET", "whsec_test"
    ), patch("routes.billing.stripe.Webhook.construct_event", side_effect=ValueError("bad sig")):
        response = client.post(
            "/-/billing/webhook",
            data="{}",
            content_type="application/json",
            headers={"Stripe-Signature": "bad"},
        )
    assert response.status_code == 400
