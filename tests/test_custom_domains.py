from unittest.mock import MagicMock, patch

from app import app
from db import (
    create_post,
    create_user_and_site,
    get_site_by_subdomain,
    set_custom_domain,
    verify_custom_domain,
)

SITE_HOST = "myblog.jottit.localhost:8000"


def _setup_site():
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    return user, site


def test_add_domain_generates_token(client):
    user, site = _setup_site()
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post(
        "/settings/domain",
        data={"domain": "example.com"},
        headers={"Host": SITE_HOST},
    )
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["custom_domain"] == "example.com"
    assert updated["domain_verification_token"] is not None
    assert updated["domain_verified_at"] is None


def test_add_domain_shown_in_settings(client):
    user, site = _setup_site()
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post(
        "/settings/domain",
        data={"domain": "example.com"},
        headers={"Host": SITE_HOST},
    )
    response = client.get("/settings", headers={"Host": SITE_HOST})
    assert b"example.com" in response.data
    assert b"not yet verified" in response.data


def test_add_domain_invalid_format(client):
    user, site = _setup_site()
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/settings/domain",
        data={"domain": "nodots"},
        headers={"Host": SITE_HOST},
    )
    assert b"Enter a valid domain name" in response.data


def test_add_domain_rejects_protocol_prefix(client):
    user, site = _setup_site()
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/settings/domain",
        data={"domain": "https://example.com"},
        headers={"Host": SITE_HOST},
    )
    assert b"Enter a valid domain name" in response.data


def test_add_domain_already_claimed(client):
    user, site = _setup_site()
    with app.app_context():
        create_user_and_site("other@example.com", "other")
        other = get_site_by_subdomain("other")
        set_custom_domain(other["id"], "taken.com", "tok")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/settings/domain",
        data={"domain": "taken.com"},
        headers={"Host": SITE_HOST},
    )
    assert b"already in use" in response.data


def test_verify_with_correct_txt_record(client):
    user, site = _setup_site()
    with app.app_context():
        updated = set_custom_domain(site["id"], "example.com", "mytoken123")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]

    mock_answer = MagicMock()
    mock_answer.__str__ = lambda self: '"jottit-site-verification=mytoken123"'
    with patch("routes.dns.resolver.resolve", return_value=[mock_answer]):
        response = client.post(
            "/settings/domain/verify",
            headers={"Host": SITE_HOST},
        )

    assert response.status_code == 302
    with app.app_context():
        verified = get_site_by_subdomain("myblog")
    assert verified["domain_verified_at"] is not None


def test_verify_with_missing_txt_record(client):
    user, site = _setup_site()
    with app.app_context():
        set_custom_domain(site["id"], "example.com", "mytoken123")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]

    with patch("routes.dns.resolver.resolve", side_effect=Exception("NXDOMAIN")):
        response = client.post(
            "/settings/domain/verify",
            headers={"Host": SITE_HOST},
        )

    assert b"TXT record not found" in response.data


def test_remove_domain(client):
    user, site = _setup_site()
    with app.app_context():
        set_custom_domain(site["id"], "example.com", "tok")
        verify_custom_domain(site["id"])
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    client.post("/settings/domain/remove", headers={"Host": SITE_HOST})
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["custom_domain"] is None
    assert updated["domain_verified_at"] is None
    assert updated["domain_verification_token"] is None


def test_tls_ask_returns_200_for_verified_domain(client):
    user, site = _setup_site()
    with app.app_context():
        set_custom_domain(site["id"], "example.com", "tok")
        verify_custom_domain(site["id"])
    app.config["CADDY_ASK_TOKEN_OVERRIDE"] = "secret"
    with patch("routes.CADDY_ASK_TOKEN", "secret"):
        response = client.get("/_tls/ask?token=secret&domain=example.com")
    assert response.status_code == 200


def test_tls_ask_returns_403_for_unverified_domain(client):
    user, site = _setup_site()
    with app.app_context():
        set_custom_domain(site["id"], "example.com", "tok")
    with patch("routes.CADDY_ASK_TOKEN", "secret"):
        response = client.get("/_tls/ask?token=secret&domain=example.com")
    assert response.status_code == 403


def test_tls_ask_returns_403_for_wrong_token(client):
    user, site = _setup_site()
    with app.app_context():
        set_custom_domain(site["id"], "example.com", "tok")
        verify_custom_domain(site["id"])
    with patch("routes.CADDY_ASK_TOKEN", "secret"):
        response = client.get("/_tls/ask?token=wrong&domain=example.com")
    assert response.status_code == 403


def test_custom_domain_routes_to_correct_site(client):
    user, site = _setup_site()
    with app.app_context():
        create_post(site["id"], "hello", "Hello World", "Body text")
        set_custom_domain(site["id"], "example.com", "tok")
        verify_custom_domain(site["id"])
    response = client.get("/", headers={"Host": "example.com"})
    assert response.status_code == 200
    assert b"Hello World" in response.data


def test_subdomain_redirects_unauthenticated_to_custom_domain(client):
    user, site = _setup_site()
    with app.app_context():
        set_custom_domain(site["id"], "example.com", "tok")
        verify_custom_domain(site["id"])
    response = client.get("/", headers={"Host": SITE_HOST})
    assert response.status_code == 308
    assert "example.com" in response.headers["Location"]


def test_subdomain_no_redirect_for_authenticated_owner(client):
    user, site = _setup_site()
    with app.app_context():
        set_custom_domain(site["id"], "example.com", "tok")
        verify_custom_domain(site["id"])
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/", headers={"Host": SITE_HOST})
    assert response.status_code == 200


def test_drafts_hidden_on_custom_domain(client):
    user, site = _setup_site()
    with app.app_context():
        create_post(site["id"], "my-draft", "My Draft", "Secret", is_draft=True)
        create_post(site["id"], "published", "Published", "Public")
        set_custom_domain(site["id"], "example.com", "tok")
        verify_custom_domain(site["id"])
    response = client.get("/", headers={"Host": "example.com"})
    assert b"Published" in response.data
    assert b"My Draft" not in response.data
