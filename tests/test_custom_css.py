import io

from app import app
from db import create_post, create_user_and_site, get_site_by_subdomain, update_site_custom_css


def test_download_default_theme(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/-/download-theme", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert response.content_type == "text/css; charset=utf-8"
    assert b"Theme: Default" in response.data
    assert b"Author: myblog" in response.data
    assert 'attachment; filename="theme.css"' in response.headers["Content-Disposition"]


def test_download_custom_theme(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site_custom_css(site["id"], "body { color: red; }")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/-/download-theme", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert b"Theme: Custom" in response.data
    assert b"body { color: red; }" in response.data


def test_upload_css(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    data = {"css_file": (io.BytesIO(b"body { color: blue; }"), "theme.css")}
    response = client.post(
        "/-/design/upload-css",
        data=data,
        content_type="multipart/form-data",
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["custom_css"] == "body { color: blue; }"


def test_upload_empty_file_rejected(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    data = {"css_file": (io.BytesIO(b""), "empty.css")}
    response = client.post(
        "/-/design/upload-css",
        data=data,
        content_type="multipart/form-data",
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["custom_css"] is None


def test_remove_custom_css(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site_custom_css(site["id"], "body { color: red; }")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/-/design/remove-css",
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["custom_css"] is None


def test_site_serves_custom_css_inline(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site_custom_css(site["id"], "body { color: red; }")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert b"<style>body { color: red; }</style>" in response.data
    assert b'href="/static/theme.css"' not in response.data


def test_site_serves_default_theme_when_no_custom_css(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert b'href="/static/theme.css"' in response.data


def test_post_serves_custom_css_inline(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Hello", "World")
        update_site_custom_css(site["id"], "article { margin: 0; }")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/hello", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert b"<style>article { margin: 0; }</style>" in response.data


def test_design_page_shows_custom_theme_status(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site_custom_css(site["id"], "body { color: red; }")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/-/design", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert b"Using custom theme" in response.data
    assert b"Remove custom theme" in response.data
