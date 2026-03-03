import io
from unittest.mock import patch

from app import app
from auth import hash_passcode, verify_passcode
from db import create_post, create_user_and_site, get_db, get_site_by_subdomain
from routes.design import sanitize_css

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def setup_site(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    return user, site


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


# ── CSS sanitization ────────────────────


def test_sanitize_css_strips_style_tag():
    assert "</style>" not in sanitize_css("body {} </style><script>alert(1)</script>")


def test_sanitize_css_strips_import():
    result = sanitize_css("@import url('evil.css'); body { color: red; }")
    assert "@import" not in result
    assert "body { color: red; }" in result


def test_sanitize_css_strips_expression():
    result = sanitize_css("div { width: expression(alert(1)); }")
    assert "expression" not in result.lower()


def test_sanitize_css_strips_javascript():
    result = sanitize_css("div { background: javascript:alert(1); }")
    assert "javascript" not in result.lower()


def test_sanitize_css_strips_behavior():
    result = sanitize_css("div { behavior: url(xss.htc); }")
    assert "behavior" not in result.lower()


def test_sanitize_css_strips_moz_binding():
    result = sanitize_css("div { -moz-binding: url('evil.xml#xss'); }")
    assert "-moz-binding" not in result.lower()


def test_sanitize_css_preserves_normal_css():
    css = "body { color: red; font-size: 16px; }\n.header { background: #fff; }"
    assert sanitize_css(css) == css


def test_upload_css_sanitized(client):
    user, site = setup_site(client)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    malicious = "@import url('evil.css'); body { color: red; }"
    data = {"css_file": (io.BytesIO(malicious.encode()), "theme.css")}
    client.post(
        "/-/design/upload-css",
        data=data,
        content_type="multipart/form-data",
        headers=HOST,
    )
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert "@import" not in updated["custom_css"]
    assert "body { color: red; }" in updated["custom_css"]


# ── Signup subdomain validation ──────────


@patch("routes.auth.send_passcode")
def test_signup_rejects_invalid_subdomain(mock_send, client):
    response = client.post("/signup", data={"subdomain": "---", "email": "u@example.com"})
    assert response.status_code == 302
    mock_send.assert_not_called()


@patch("routes.auth.send_passcode")
def test_signup_accepts_valid_subdomain(mock_send, client):
    response = client.post("/signup", data={"subdomain": "goodname", "email": "u@example.com"})
    assert response.status_code == 200
    mock_send.assert_called_once()


# ── Open redirect prevention ─────────────


def test_comment_delete_safe_redirect(client):
    user, site = setup_site(client)
    with app.app_context():
        db = get_db()
        db.execute("UPDATE sites SET comments_enabled = TRUE WHERE id = %s", (site["id"],))
        db.commit()
        post = create_post(site["id"], "hello", "Hello", "Body")
        from db import create_comment

        comment = create_comment(post["id"], site["id"], "Someone", "abc", "Test")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        f"/-/comment/{comment['id']}/delete",
        headers={**HOST, "Referer": "https://evil.com/steal"},
    )
    assert response.status_code == 302
    assert "evil.com" not in response.headers["Location"]


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
