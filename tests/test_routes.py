import io
import zipfile
from pathlib import Path
from unittest.mock import patch

from app import app
from db import (
    create_page,
    create_post,
    create_subscriber,
    create_user_and_site,
    get_page_by_slug,
    get_post_by_slug,
    get_subscriber,
    update_page,
    update_site_avatar,
)

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def _setup(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    return user, site


# ── require_owner: no site ──────────────────────


def test_require_owner_no_site(client):
    response = client.get("/-/edit", headers={"Host": "nosuchsite.tinypost.localhost:8000"})
    assert response.status_code == 404


# ── Home POST (signup flow) ────────────────────


def test_home_post_invalid_subdomain(client):
    response = client.post("/", data={"subdomain": "x"})
    assert response.status_code == 200
    assert b"Invalid name" in response.data


def test_home_post_taken_subdomain(client, taken_subdomain):
    response = client.post("/", data={"subdomain": taken_subdomain})
    assert response.status_code == 200
    assert b"is not available" in response.data


def test_home_post_valid_subdomain(client):
    response = client.post("/", data={"subdomain": "newblog"})
    assert response.status_code == 200
    assert b"newblog" in response.data


# ── Signup ──────────────────────────────────────


@patch("routes.auth.send_passcode")
def test_signup_post(mock_send, client):
    response = client.post("/signup", data={"subdomain": "fresh", "email": "u@example.com"})
    assert response.status_code == 200
    assert b"u@example.com" in response.data
    mock_send.assert_called_once()


def test_signup_verify_success(client):
    with client.session_transaction() as sess:
        sess["signup"] = {"subdomain": "fresh", "email": "u@example.com", "passcode": "123456"}
    response = client.post("/verify", data={"passcode": "123456"})
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" in sess


def test_signup_verify_wrong_code(client):
    with client.session_transaction() as sess:
        sess["signup"] = {"subdomain": "fresh", "email": "u@example.com", "passcode": "123456"}
    response = client.post("/verify", data={"passcode": "000000"})
    assert response.status_code == 200
    assert b"Wrong passcode" in response.data


def test_signup_verify_no_session(client):
    response = client.post("/verify", data={"passcode": "123456"})
    assert response.status_code == 302


# ── Signin ──────────────────────────────────────


def test_signin_get(client):
    response = client.get("/signin")
    assert response.status_code == 200


@patch("routes.auth.send_passcode")
def test_signin_post_success(mock_send, client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.post("/signin", data={"email": "owner@example.com"})
    assert response.status_code == 200
    mock_send.assert_called_once()


def test_signin_post_unknown_email(client):
    response = client.post("/signin", data={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert b"No account" in response.data


def test_signin_verify_success(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["signin"] = {"email": "owner@example.com", "user_id": user["id"], "passcode": "123456"}
    response = client.post("/signin/verify", data={"passcode": "123456"})
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_id"] == user["id"]


def test_signin_verify_wrong_code(client):
    with client.session_transaction() as sess:
        sess["signin"] = {"email": "u@example.com", "user_id": 1, "passcode": "123456"}
    response = client.post("/signin/verify", data={"passcode": "000000"})
    assert response.status_code == 200
    assert b"Wrong passcode" in response.data


def test_signin_verify_no_session(client):
    response = client.post("/signin/verify", data={"passcode": "123456"})
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
    _, site = _setup(client)
    response = client.post("/-/edit", data={"title": "Hello", "body": "World"}, headers=HOST)
    assert response.status_code == 302
    with app.app_context():
        post = get_post_by_slug(site["id"], "hello")
    assert post is not None
    assert post["title"] == "Hello"


def test_edit_create_draft(client):
    _, site = _setup(client)
    response = client.post(
        "/-/edit", data={"title": "Draft", "body": "Content", "is_draft": "on"}, headers=HOST
    )
    assert response.status_code == 302
    with app.app_context():
        post = get_post_by_slug(site["id"], "draft")
    assert post["is_draft"] is True


# ── Edit existing post ──────────────────────────


def test_edit_post_not_found(client):
    _setup(client)
    response = client.get("/-/edit/nonexistent", headers=HOST)
    assert response.status_code == 404


def test_edit_post_get(client):
    _, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
    response = client.get("/-/edit/hello", headers=HOST)
    assert response.status_code == 200
    assert b"Hello" in response.data


def test_edit_existing_post_empty_body(client):
    _, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
    response = client.post("/-/edit/hello", data={"title": "Hello", "body": ""}, headers=HOST)
    assert response.status_code == 200
    assert b"body is required" in response.data


def test_edit_post_page_slug_conflict(client):
    _, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
        page = create_page(site["id"], "about", "About")
        update_page(page["id"], "About", "About body", is_draft=False)
    response = client.post(
        "/-/edit/hello", data={"title": "About", "body": "New body"}, headers=HOST
    )
    assert response.status_code == 200
    assert b"page already uses" in response.data


# ── Delete post ─────────────────────────────────


def test_delete_post(client):
    _, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
    response = client.post("/-/delete/hello", headers=HOST)
    assert response.status_code == 302
    with app.app_context():
        assert get_post_by_slug(site["id"], "hello") is None


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
    _, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Body")
    response = client.post("/-/send/hello", headers=HOST)
    assert response.status_code == 302
    mock_send.assert_not_called()


# ── Subscribers ─────────────────────────────────


def test_subscribers_page(client):
    _, site = _setup(client)
    with app.app_context():
        create_subscriber(site["id"], "a@example.com", "tok-a")
    response = client.get("/-/subscribers", headers=HOST)
    assert response.status_code == 200
    assert b"a@example.com" in response.data


def test_subscribers_delete(client):
    _, site = _setup(client)
    with app.app_context():
        create_subscriber(site["id"], "a@example.com", "tok-a")
        sub = get_subscriber(site["id"], "a@example.com")
    response = client.post(f"/-/subscribers/delete/{sub['id']}", headers=HOST)
    assert response.status_code == 302


# ── Settings: avatar edge cases ─────────────────


def test_settings_avatar_no_file(client):
    _setup(client)
    response = client.post("/-/settings/avatar", headers=HOST)
    assert response.status_code == 302
    assert "/-/settings" in response.headers["Location"]


@patch("routes.settings.delete_image")
def test_settings_avatar_delete_external_url(mock_delete, client):
    _, site = _setup(client)
    with app.app_context():
        update_site_avatar(site["id"], "https://cdn.example.com/myblog/avatar.png")
    response = client.post("/-/settings/avatar/delete", headers=HOST)
    assert response.status_code == 302
    mock_delete.assert_called_once_with("myblog/avatar.png")


# ── Settings: export pages ──────────────────────


def test_export_contains_pages(client):
    _, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About")
        update_page(page["id"], "About", "About me", is_draft=False)
    response = client.get("/-/settings/export", headers=HOST)
    zf = zipfile.ZipFile(io.BytesIO(response.data))
    assert "pages/about.md" in zf.namelist()
    content = zf.read("pages/about.md").decode()
    assert "# About" in content
    assert "About me" in content


def test_export_page_without_body(client):
    _, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "empty", "Empty Page")
    response = client.get("/-/settings/export", headers=HOST)
    zf = zipfile.ZipFile(io.BytesIO(response.data))
    content = zf.read("pages/empty.md").decode()
    assert content == "# Empty Page"


# ── Settings: domain verify without domain ──────


def test_domain_verify_no_domain_set(client):
    _setup(client)
    response = client.post("/-/settings/domain/verify", headers=HOST)
    assert response.status_code == 302
    assert "/-/settings" in response.headers["Location"]


# ── Design: invalid font_body ───────────────────


def test_design_invalid_font_body(client):
    _setup(client)
    response = client.post(
        "/-/design",
        data={"font_header": "", "font_body": "Comic Sans MS"},
        headers=HOST,
    )
    assert response.status_code == 302


# ── CSS upload: no file ─────────────────────────


def test_upload_css_no_file(client):
    _setup(client)
    response = client.post("/-/design/upload-css", headers=HOST)
    assert response.status_code == 302
    assert "/-/design" in response.headers["Location"]


# ── New page ────────────────────────────────────


def test_new_page_get(client):
    _setup(client)
    response = client.get("/-/new-page", headers=HOST)
    assert response.status_code == 200


def test_new_page_success(client):
    _, site = _setup(client)
    response = client.post(
        "/-/new-page",
        data={"title": "Contact", "body": "Email me"},
        headers=HOST,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_page_by_slug(site["id"], "contact") is not None


def test_new_page_no_title(client):
    _setup(client)
    response = client.post("/-/new-page", data={"title": "", "body": "Body"}, headers=HOST)
    assert response.status_code == 200
    assert b"Title is required" in response.data


def test_new_page_slug_conflict(client):
    _, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "contact", "Contact", "Body")
    response = client.post(
        "/-/new-page",
        data={"title": "Contact", "body": "Page body"},
        headers=HOST,
    )
    assert response.status_code == 200
    assert b"already taken" in response.data


def test_new_page_as_draft(client):
    _, site = _setup(client)
    response = client.post(
        "/-/new-page",
        data={"title": "Hidden", "body": "Secret", "is_draft": "on"},
        headers=HOST,
    )
    assert response.status_code == 302
    with app.app_context():
        page = get_page_by_slug(site["id"], "hidden")
    assert page["is_draft"] is True


# ── Edit page ───────────────────────────────────


def test_edit_page_not_found(client):
    _setup(client)
    response = client.get("/-/edit-page/nonexistent", headers=HOST)
    assert response.status_code == 404


def test_edit_page_get(client):
    _, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    response = client.get("/-/edit-page/about", headers=HOST)
    assert response.status_code == 200
    assert b"About" in response.data


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
        create_user_and_site("owner@example.com", "myblog")
    response = client.post("/subscribe", data={"email": ""}, headers=HOST)
    assert response.status_code == 302
    mock_send.assert_not_called()


# ── Post/page slug: 404 when neither found ──────


def test_slug_not_found(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
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
        create_user_and_site("owner@example.com", "myblog")
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
        create_user_and_site("owner@example.com", "myblog")

    app.config["TESTING"] = False
    try:
        with patch("routes.home.get_current_site", side_effect=RuntimeError("boom")):
            response = client.get("/", headers=HOST)
    finally:
        app.config["TESTING"] = True
    assert response.status_code == 500
    assert b"Something went wrong" in response.data
    assert b"support@tinypost.blog" in response.data
