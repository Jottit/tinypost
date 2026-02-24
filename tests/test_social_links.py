from app import app
from db import create_user_and_site, get_site_by_subdomain, update_site


def login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]


def test_social_links_saved(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user)
    response = client.post(
        "/-/settings",
        data={
            "title": "My Blog",
            "bio": "",
            "license": "",
            "social_links[0][label]": "Mastodon",
            "social_links[0][url]": "https://mastodon.social/@test",
            "social_links[1][label]": "GitHub",
            "social_links[1][url]": "https://github.com/test",
        },
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert len(updated["social_links"]) == 2
    assert updated["social_links"][0]["label"] == "Mastodon"
    assert updated["social_links"][0]["url"] == "https://mastodon.social/@test"
    assert updated["social_links"][1]["label"] == "GitHub"


def test_empty_social_links_skipped(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user)
    response = client.post(
        "/-/settings",
        data={
            "title": "My Blog",
            "bio": "",
            "license": "",
            "social_links[0][label]": "",
            "social_links[0][url]": "",
            "social_links[1][label]": "GitHub",
            "social_links[1][url]": "https://github.com/test",
        },
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert len(updated["social_links"]) == 1
    assert updated["social_links"][0]["label"] == "GitHub"


def test_social_links_displayed_on_blog(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site(
            site["id"],
            "My Blog",
            None,
            social_links=[
                {"label": "Mastodon", "url": "https://mastodon.social/@test"},
                {"label": "GitHub", "url": "https://github.com/test"},
            ],
        )
    response = client.get("/", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    html = response.data.decode()
    assert 'rel="me"' in html
    assert "https://mastodon.social/@test" in html
    assert "https://github.com/test" in html


def test_social_links_in_settings_form(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site(
            site["id"],
            "My Blog",
            None,
            social_links=[{"label": "GitHub", "url": "https://github.com/test"}],
        )
    login(client, user)
    response = client.get("/-/settings", headers={"Host": "myblog.jottit.localhost:8000"})
    html = response.data.decode()
    assert "https://github.com/test" in html
    assert "GitHub" in html
