from app import app
from db import (
    create_page,
    create_post,
    create_user_and_site,
    get_page_by_id,
    update_page,
    update_site,
)

SITE_HOST = "myblog.tinypost.localhost:8000"


def _setup(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    return user, site


def test_create_post_slug_conflict_with_page(client):
    _, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    response = client.post(
        "/-/edit",
        data={"title": "About", "body": "Some content"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    assert b"reserved or already in use" in response.data


def test_draft_page_hidden_from_public_nav(client):
    _, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About", is_draft=True)
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"About" not in response.data


def test_menu_shown_in_nav(client):
    _, site = _setup(client)
    with app.app_context():
        update_site(site["id"], site["title"], None, menu="About")
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"About" in response.data


def test_menu_custom_label(client):
    _, site = _setup(client)
    with app.app_context():
        update_site(site["id"], site["title"], None, menu="Home: index")
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"Home" in response.data
    assert b"/index" in response.data


def test_page_renders_at_slug(client):
    _, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About")
        update_page(page["id"], "About", "All about me", is_draft=False)
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/about", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"About" in response.data
    assert b"All about me" in response.data


def test_draft_page_404_for_public(client):
    _, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About", is_draft=True)
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/about", headers={"Host": SITE_HOST})
    assert response.status_code == 404


def test_draft_page_visible_to_owner(client):
    _, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    response = client.get("/about", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"About" in response.data


def test_edit_page_body_and_publish(client):
    _, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About")
        page_id = page["id"]
    response = client.post(
        "/-/edit-page/about",
        data={"title": "About", "body": "Updated body"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    with app.app_context():
        page = get_page_by_id(page_id)
    assert page["body"] == "Updated body"
    assert page["is_draft"] is False


def test_posts_take_priority_over_pages(client):
    _, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello Post", "Post body")
        page = create_page(site["id"], "hello-page", "Hello Page")
        update_page(page["id"], "Hello Page", "Page body", is_draft=False)
    response = client.get("/hello", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"Post body" in response.data


def test_pages_not_in_rss_feed(client):
    _, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About")
        update_page(page["id"], "About", "About body", is_draft=False)
        create_post(site["id"], "hello", "Hello", "Post body")
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    assert b"About" not in response.data
    assert b"Hello" in response.data


def test_owner_sees_add_menu_link(client):
    _setup(client)
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"add menu" in response.data


def test_public_does_not_see_add_menu_link(client):
    _setup(client)
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"add menu" not in response.data


def test_add_menu_link_hidden_when_menu_set(client):
    _, site = _setup(client)
    with app.app_context():
        update_site(site["id"], site["title"], None, menu="About")
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"add menu" not in response.data


def test_menu_link_to_missing_page_redirects_to_editor(client):
    _, site = _setup(client)
    with app.app_context():
        update_site(site["id"], site["title"], None, menu="About")
    response = client.get("/about", headers={"Host": SITE_HOST})
    assert response.status_code == 302
    assert "/-/new-page" in response.headers["Location"]
    assert "title=About" in response.headers["Location"]


def test_menu_link_to_missing_page_404_for_public(client):
    _, site = _setup(client)
    with app.app_context():
        update_site(site["id"], site["title"], None, menu="About")
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/about", headers={"Host": SITE_HOST})
    assert response.status_code == 404


def test_edit_page_title_required(client):
    _, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    response = client.post(
        "/-/edit-page/about",
        data={"title": "", "body": "Some body"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    assert b"Title is required" in response.data
