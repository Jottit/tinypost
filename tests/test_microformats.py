from app import app
from db import create_post, create_user_and_site, update_site


def test_blog_index_has_h_feed(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Hello World", "Body text")
    response = client.get("/", headers={"Host": "myblog.tinypost.localhost:8000"})
    html = response.data.decode()
    assert "h-feed" in html
    assert "h-entry" in html
    assert "dt-published" in html
    assert "p-name" in html


def test_post_page_has_h_entry(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Hello World", "Body text")
    response = client.get("/hello", headers={"Host": "myblog.tinypost.localhost:8000"})
    html = response.data.decode()
    assert "h-entry" in html
    assert "p-name" in html
    assert "e-content" in html
    assert "dt-published" in html
    assert "u-url" in html
    assert "p-author" in html


def test_site_header_has_h_card(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Hello World", "Body text")
    response = client.get("/", headers={"Host": "myblog.tinypost.localhost:8000"})
    html = response.data.decode()
    assert "h-card" in html
    assert "p-name" in html
    assert "u-url" in html


def test_social_links_have_rel_me(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site(
            site["id"],
            "My Blog",
            None,
            social_links=[{"label": "Mastodon", "url": "https://mastodon.social/@test"}],
        )
        create_post(site["id"], "hello", "Hello World", "Body text")
    response = client.get("/", headers={"Host": "myblog.tinypost.localhost:8000"})
    html = response.data.decode()
    assert 'rel="me"' in html
    assert 'class="u-url"' in html
    assert "https://mastodon.social/@test" in html


def test_custom_domain_in_u_url(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        from db import get_db

        db = get_db()
        db.execute(
            "UPDATE sites SET custom_domain = %s, domain_verified_at = NOW() WHERE id = %s",
            ("blog.example.com", site["id"]),
        )
        db.commit()
        create_post(site["id"], "hello", "Hello World", "Body text")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/hello", headers={"Host": "myblog.tinypost.localhost:8000"})
    html = response.data.decode()
    assert "https://blog.example.com" in html
