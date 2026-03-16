from app import app
from db import create_user, get_user_by_subdomain


def login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]


def test_appearance_requires_auth(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    response = client.get("/-/settings/theme", headers={"Host": "myblog.tinypost.localhost:8000"})
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_appearance_page_renders(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    response = client.get("/-/settings/theme", headers={"Host": "myblog.tinypost.localhost:8000"})
    assert response.status_code == 200
    assert b"Light" in response.data
    assert b"Dark" in response.data


def test_appearance_save_updates_preset(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    response = client.post(
        "/-/settings/theme",
        data={"preset": "dark"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert updated["theme"] == "dark"


def test_appearance_applies_to_homepage(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    client.post(
        "/-/settings/theme",
        data={"preset": "dark"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    response = client.get("/", headers={"Host": "myblog.tinypost.localhost:8000"})
    assert response.status_code == 200
    assert b"--site-bg: #07131c" in response.data
    assert b"--site-accent: #86b3ff" in response.data


def test_accent_color_saves(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    client.post(
        "/-/settings/theme",
        data={"preset": "light", "accent_color": "#c05838"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert updated["accent_color"] == "#c05838"


def test_accent_color_applies_to_homepage(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    client.post(
        "/-/settings/theme",
        data={"preset": "light", "accent_color": "#c05838"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    response = client.get("/", headers={"Host": "myblog.tinypost.localhost:8000"})
    assert response.status_code == 200
    assert b"--site-accent: #c05838" in response.data


def test_invalid_accent_color_ignored(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    client.post(
        "/-/settings/theme",
        data={"preset": "light", "accent_color": "notahex"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert updated["accent_color"] is None
