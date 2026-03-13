from app import app
from db import create_user, get_user_by_subdomain


def test_settings_requires_auth(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.get("/-/settings", headers={"Host": "myblog.tinypost.localhost:8000"})
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_settings_get(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/-/settings", headers={"Host": "myblog.tinypost.localhost:8000"})
    assert response.status_code == 200
    assert b"Settings" in response.data


def test_settings_update(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/-/settings/blog",
        data={"title": "New Title", "bio": "A short bio"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert updated["title"] == "New Title"
    assert updated["bio"] == "A short bio"


def test_settings_title_required(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/-/settings/blog",
        data={"title": "", "bio": "bio"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    assert response.status_code == 200
    assert b"Title is required" in response.data
