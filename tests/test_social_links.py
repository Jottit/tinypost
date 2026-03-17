from app import app
from db import create_user, get_user_by_subdomain, update_user_links


def login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]


def test_social_links_saved(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    client.post(
        "/-/settings/links/add",
        data={"label": "Mastodon", "url": "https://mastodon.social/@test"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    response = client.post(
        "/-/settings/links/add",
        data={"label": "GitHub", "url": "https://github.com/test"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert len(updated["links"]) == 2
    assert updated["links"][0]["label"] == "Mastodon"
    assert updated["links"][0]["url"] == "https://mastodon.social/@test"
    assert updated["links"][1]["label"] == "GitHub"


def test_url_only_link_allowed(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    response = client.post(
        "/-/settings/links/add",
        data={"label": "", "url": "https://example.com"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert len(updated["links"]) == 1
    assert updated["links"][0]["label"] == ""
    assert updated["links"][0]["url"] == "https://example.com"


def test_bare_domain_gets_https(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    client.post(
        "/-/settings/links/add",
        data={"label": "Site", "url": "example.com"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert updated["links"][0]["url"] == "https://example.com"


def test_social_links_displayed_on_blog(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        update_user_links(
            user["id"],
            [
                {"label": "Mastodon", "url": "https://mastodon.social/@test"},
                {"label": "GitHub", "url": "https://github.com/test"},
            ],
        )
    response = client.get("/", headers={"Host": "myblog.tinypost.localhost:8000"})
    assert response.status_code == 200
    html = response.data.decode()
    assert 'rel="me"' in html
    assert "https://mastodon.social/@test" in html
    assert "https://github.com/test" in html


def test_social_links_in_settings(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        update_user_links(
            user["id"],
            [{"label": "GitHub", "url": "https://github.com/test"}],
        )
    login(client, user)
    response = client.get("/-/settings/links", headers={"Host": "myblog.tinypost.localhost:8000"})
    html = response.data.decode()
    assert "github.com" in html
    assert "GitHub" in html


def test_remove_link(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
        update_user_links(
            user["id"],
            [
                {"label": "GitHub", "url": "https://github.com/test"},
                {"label": "Mastodon", "url": "https://mastodon.social/@test"},
            ],
        )
    login(client, user)
    response = client.post(
        "/-/settings/links/remove",
        data={"index": "0"},
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert len(updated["links"]) == 1
    assert updated["links"][0]["label"] == "Mastodon"


def test_old_social_url_redirects(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    login(client, user)
    response = client.get(
        "/-/settings/social",
        headers={"Host": "myblog.tinypost.localhost:8000"},
    )
    assert response.status_code == 301
    assert response.headers["Location"].endswith("/-/settings/links")
