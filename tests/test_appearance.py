from app import app
from db import create_user_and_site, get_site_by_subdomain


def login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]


def test_appearance_requires_auth(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get(
        "/-/settings/appearance", headers={"Host": "myblog.tinypost.localhost:8000"}
    )
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_appearance_page_renders(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user)
    response = client.get(
        "/-/settings/appearance", headers={"Host": "myblog.tinypost.localhost:8000"}
    )
    assert response.status_code == 200
    assert b"Appearance" in response.data
    assert b"White" in response.data
    assert b"Black" in response.data


def test_appearance_save_updates_preset(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user)
    response = client.post(
        "/-/settings/appearance",
        data={"preset": "blue"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["design"]["preset"] == "blue"


def test_appearance_applies_to_homepage(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user)
    client.post(
        "/-/settings/appearance",
        data={"preset": "green"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    response = client.get("/", headers={"Host": "myblog.tinypost.localhost:8000"})
    assert response.status_code == 200
    assert b"--site-bg: #eef4ea" in response.data
    assert b"--site-accent: #2db36b" in response.data
