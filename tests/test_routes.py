from pathlib import Path
from unittest.mock import patch

from app import app
from auth import hash_passcode
from db import (
    create_post,
    create_user,
    get_post_by_slug,
    toggle_post_pinned,
    update_user_avatar,
)

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def _setup(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    return user


# ── require_owner: no site ──────────────────────


def test_require_owner_no_site(client):
    response = client.get("/-/edit", headers={"Host": "nosuchsite.tinypost.localhost:8000"})
    assert response.status_code == 404


# ── Signup flow ────────────────────────────────


def test_signup_get(client):
    response = client.get("/signup")
    assert response.status_code == 200


@patch("routes.auth.send_passcode")
def test_signup_email_send(mock_send, client):
    response = client.post("/signup/email/send", data={"email": "u@example.com"})
    assert response.status_code == 200
    mock_send.assert_called_once()


def test_signup_verify_success(client):
    with client.session_transaction() as sess:
        sess["signup"] = {
            "email": "u@example.com",
            "passcode": hash_passcode("123456"),
        }
    response = client.post("/signup/verify", data={"passcode": "123456"})
    assert response.status_code == 200
    assert b"name" in response.data.lower()


def test_signup_verify_wrong_code(client):
    with client.session_transaction() as sess:
        sess["signup"] = {
            "email": "u@example.com",
            "passcode": hash_passcode("123456"),
        }
    response = client.post("/signup/verify", data={"passcode": "000000"})
    assert response.status_code == 200
    assert b"Wrong passcode" in response.data


def test_signup_name(client):
    with client.session_transaction() as sess:
        sess["signup"] = {
            "email": "u@example.com",
            "passcode": hash_passcode("123456"),
            "verified": True,
        }
    response = client.post("/signup/name", data={"name": "Test User"})
    assert response.status_code == 200
    assert b"tinypost.blog" in response.data


def test_signup_verify_no_session(client):
    response = client.post("/signup/verify", data={"passcode": "123456"})
    assert response.status_code == 302


def test_signup_address_creates_user(client):
    with client.session_transaction() as sess:
        sess["signup"] = {
            "name": "Test",
            "email": "u@example.com",
            "passcode": hash_passcode("123456"),
            "verified": True,
        }
    response = client.post("/signup/address", data={"subdomain": "fresh"})
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" in sess


def test_signup_address_rejects_invalid(client):
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


# ── Signin ──────────────────────────────────────


def test_signin_get(client):
    response = client.get("/signin")
    assert response.status_code == 200


@patch("routes.auth.send_passcode")
def test_signin_post_success(mock_send, client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.post("/signin", data={"email": "owner@example.com"})
    assert response.status_code == 200
    mock_send.assert_called_once()


def test_signin_post_unknown_email(client):
    response = client.post("/signin", data={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert b"No account" in response.data


def test_signin_verify_success(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["signin"] = {
            "email": "owner@example.com",
            "user_id": user["id"],
            "passcode": hash_passcode("123456"),
        }
    response = client.post("/signin/verify", data={"passcode": "123456"})
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_id"] == user["id"]


def test_signin_verify_wrong_code(client):
    with client.session_transaction() as sess:
        sess["signin"] = {
            "email": "u@example.com",
            "user_id": 1,
            "passcode": hash_passcode("123456"),
        }
    response = client.post("/signin/verify", data={"passcode": "000000"})
    assert response.status_code == 200
    assert b"Wrong passcode" in response.data


def test_signin_verify_no_session(client):
    response = client.post("/signin/verify", data={"passcode": hash_passcode("123456")})
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


# ── Signout ─────────────────────────────────────


def test_signout(client):
    _setup(client)
    response = client.post("/signout", headers=HOST)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" not in sess


# ── Edit (create new post) ──────────────────────


def test_edit_new_post_empty_body(client):
    _setup(client)
    response = client.post("/-/edit", data={"title": "Hello", "body": ""}, headers=HOST)
    assert response.status_code == 200
    assert b"body is required" in response.data


def test_edit_create_post_success(client):
    user = _setup(client)
    response = client.post("/-/edit", data={"title": "Hello", "body": "World"}, headers=HOST)
    assert response.status_code == 302
    with app.app_context():
        post = get_post_by_slug(user["id"], "hello")
    assert post is not None
    assert post["title"] == "Hello"


def test_edit_create_draft(client):
    user = _setup(client)
    response = client.post(
        "/-/edit", data={"title": "Draft", "body": "Content", "is_draft": "on"}, headers=HOST
    )
    assert response.status_code == 302
    with app.app_context():
        post = get_post_by_slug(user["id"], "draft")
    assert post["is_draft"] is True


# ── Edit existing post ──────────────────────────


def test_edit_post_not_found(client):
    _setup(client)
    response = client.get("/-/edit/nonexistent", headers=HOST)
    assert response.status_code == 404


def test_edit_post_get(client):
    user = _setup(client)
    with app.app_context():
        create_post(user["id"], "hello", "Hello", "Body")
    response = client.get("/-/edit/hello", headers=HOST)
    assert response.status_code == 200
    assert b"Hello" in response.data


def test_edit_existing_post_empty_body(client):
    user = _setup(client)
    with app.app_context():
        create_post(user["id"], "hello", "Hello", "Body")
    response = client.post("/-/edit/hello", data={"title": "Hello", "body": ""}, headers=HOST)
    assert response.status_code == 200
    assert b"body is required" in response.data


# ── Delete post ─────────────────────────────────


def test_delete_post(client):
    user = _setup(client)
    with app.app_context():
        create_post(user["id"], "hello", "Hello", "Body")
    response = client.post("/-/delete/hello", headers=HOST)
    assert response.status_code == 302
    with app.app_context():
        assert get_post_by_slug(user["id"], "hello") is None


def test_delete_post_not_found(client):
    _setup(client)
    response = client.post("/-/delete/nonexistent", headers=HOST)
    assert response.status_code == 404


# ── Send post ───────────────────────────────────


@patch("routes.posts.send_email")
def test_send_post_not_found(mock_send, client):
    _setup(client)
    response = client.post("/-/send/nonexistent", headers=HOST)
    assert response.status_code == 404


@patch("routes.posts.send_email")
def test_send_post_no_subscribers(mock_send, client):
    user = _setup(client)
    with app.app_context():
        create_post(user["id"], "hello", "Hello", "Body")
    response = client.post("/-/send/hello", headers=HOST)
    assert response.status_code == 302
    mock_send.assert_not_called()


# ── Pin/unpin posts ────────────────────────────


def test_pin_post_toggles(client):
    user = _setup(client)
    with app.app_context():
        create_post(user["id"], "hello", "Hello", "Body")
    response = client.post("/-/pin/hello", headers=HOST)
    assert response.status_code == 302
    with app.app_context():
        post = get_post_by_slug(user["id"], "hello")
    assert post["is_pinned"] is True

    response = client.post("/-/pin/hello", headers=HOST)
    assert response.status_code == 302
    with app.app_context():
        post = get_post_by_slug(user["id"], "hello")
    assert post["is_pinned"] is False


def test_pinned_post_shown_first(client):
    user = _setup(client)
    with app.app_context():
        create_post(user["id"], "old", "Old Post", "First post")
        create_post(user["id"], "new", "New Post", "Second post")
        old = get_post_by_slug(user["id"], "old")
        toggle_post_pinned(old["id"])
    response = client.get("/", headers=HOST)
    html = response.data.decode()
    old_pos = html.index("Old Post")
    new_pos = html.index("New Post")
    assert old_pos < new_pos


def test_pinned_label_shown(client):
    user = _setup(client)
    with app.app_context():
        create_post(user["id"], "hello", "Hello", "Body")
        post = get_post_by_slug(user["id"], "hello")
        toggle_post_pinned(post["id"])
    response = client.get("/", headers=HOST)
    assert b"pinned-icon" in response.data


def test_pin_post_not_found(client):
    _setup(client)
    response = client.post("/-/pin/nonexistent", headers=HOST)
    assert response.status_code == 404


# ── Settings: avatar edge cases ─────────────────


def test_settings_avatar_no_file(client):
    _setup(client)
    response = client.post("/-/settings/avatar", headers=HOST)
    assert response.status_code == 302
    assert "/-/settings" in response.headers["Location"]


@patch("routes.settings.delete_image")
def test_settings_avatar_delete_external_url(mock_delete, client):
    user = _setup(client)
    with app.app_context():
        update_user_avatar(user["id"], "https://cdn.example.com/myblog/avatar.png")
    response = client.post("/-/settings/avatar/delete", headers=HOST)
    assert response.status_code == 302
    mock_delete.assert_called_once_with("myblog/avatar.png")


# ── Settings: domain verify without domain ──────


def test_domain_verify_no_domain_set(client):
    _setup(client)
    response = client.post("/-/settings/domain/verify", headers=HOST)
    assert response.status_code == 302
    assert "/-/settings" in response.headers["Location"]


# ── Delete account GET ──────────────────────────


def test_delete_account_get(client):
    _setup(client)
    response = client.get("/-/settings/delete-account", headers=HOST)
    assert response.status_code == 200
    assert b"delete" in response.data.lower()


# ── Subscribe edge cases ────────────────────────


def test_subscribe_no_site(client):
    response = client.post("/subscribe", data={"email": "a@example.com"})
    assert response.status_code == 404


@patch("routes.subscribers.send_email")
def test_subscribe_empty_email(mock_send, client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.post("/subscribe", data={"email": ""}, headers=HOST)
    assert response.status_code == 302
    mock_send.assert_not_called()


# ── Post/page slug: 404 when neither found ──────


def test_slug_not_found(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.get("/nonexistent-slug", headers=HOST)
    assert response.status_code == 404


# ── Uploaded file serving ───────────────────────


def test_uploaded_file(client):
    with app.app_context():
        dest = Path(app.instance_path) / "uploads" / "test.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"\x89PNG fake")
    response = client.get("/uploads/test.png")
    assert response.status_code == 200
    assert response.data == b"\x89PNG fake"
    dest.unlink()


# ── 404 error pages ──────────────────────


def test_404_site_page(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.get("/nonexistent-path", headers=HOST)
    assert response.status_code == 404
    assert b"Page not found" in response.data
    assert b"myblog" in response.data


def test_404_tinypost_page(client):
    response = client.get("/nonexistent-path")
    assert response.status_code == 404
    assert b"Page not found" in response.data
    assert b"Tinypost" in response.data


# ── 500 error page ───────────────────────


def test_500_error_page(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")

    app.config["TESTING"] = False
    try:
        with patch("routes.home.get_current_site", side_effect=RuntimeError("boom")):
            response = client.get("/", headers=HOST)
    finally:
        app.config["TESTING"] = True
    assert response.status_code == 500
    assert b"Something went wrong" in response.data
    assert b"support@tinypost.blog" in response.data
