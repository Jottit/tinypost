import json

from app import app
from db import (
    create_page,
    create_post,
    create_user_and_site,
    get_page_by_id,
    get_page_by_slug,
    update_page,
)

SITE_HOST = "myblog.jottit.localhost:8000"


def _setup(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    return user, site


def test_add_page_from_settings(client):
    user, site = _setup(client)
    response = client.post(
        "/settings/navigation/add",
        data={"title": "About"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    with app.app_context():
        page = get_page_by_slug(site["id"], "about")
    assert page is not None
    assert page["title"] == "About"
    assert page["is_draft"] is True


def test_add_page_empty_title(client):
    _setup(client)
    response = client.post(
        "/settings/navigation/add",
        data={"title": ""},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    assert b"Title is required" in response.data


def test_add_page_slug_conflict_with_post(client):
    user, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "about", "About", "About me")
    response = client.post(
        "/settings/navigation/add",
        data={"title": "About"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    assert b"already taken" in response.data


def test_create_post_slug_conflict_with_page(client):
    user, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    response = client.post(
        "/edit",
        data={"title": "About", "body": "Some content"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    assert b"page already uses" in response.data


def test_draft_page_hidden_from_public_nav(client):
    user, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"About" not in response.data


def test_published_page_shown_in_public_nav(client):
    user, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About")
        update_page(page["id"], "About", "About me", is_draft=False)
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"About" in response.data


def test_owner_sees_draft_pages_in_nav(client):
    user, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    response = client.get("/", headers={"Host": SITE_HOST})
    assert b"About" in response.data


def test_page_renders_at_slug(client):
    user, site = _setup(client)
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
    user, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/about", headers={"Host": SITE_HOST})
    assert response.status_code == 404


def test_draft_page_visible_to_owner(client):
    user, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    response = client.get("/about", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"About" in response.data


def test_edit_page_body_and_publish(client):
    user, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About")
        page_id = page["id"]
    response = client.post(
        "/edit-page/about",
        data={"title": "About", "body": "Updated body"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    with app.app_context():
        page = get_page_by_id(page_id)
    assert page["body"] == "Updated body"
    assert page["is_draft"] is False


def test_delete_page(client):
    user, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About")
    response = client.post(
        f"/settings/navigation/delete/{page['id']}",
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with app.app_context():
        assert get_page_by_id(page["id"]) is None


def test_reorder_pages(client):
    user, site = _setup(client)
    with app.app_context():
        p1 = create_page(site["id"], "about", "About")
        p2 = create_page(site["id"], "now", "Now")
        p3 = create_page(site["id"], "uses", "Uses")
    response = client.post(
        "/settings/navigation/reorder",
        data=json.dumps({"order": [p3["id"], p1["id"], p2["id"]]}),
        content_type="application/json",
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    with app.app_context():
        assert get_page_by_id(p3["id"])["sort_order"] == 0
        assert get_page_by_id(p1["id"])["sort_order"] == 1
        assert get_page_by_id(p2["id"])["sort_order"] == 2


def test_posts_take_priority_over_pages(client):
    user, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello Post", "Post body")
        page = create_page(site["id"], "hello-page", "Hello Page")
        update_page(page["id"], "Hello Page", "Page body", is_draft=False)
    response = client.get("/hello", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"Post body" in response.data


def test_pages_not_in_rss_feed(client):
    user, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About")
        update_page(page["id"], "About", "About body", is_draft=False)
        create_post(site["id"], "hello", "Hello", "Post body")
    with client.session_transaction() as sess:
        sess.clear()
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    assert b"About" not in response.data
    assert b"Hello" in response.data


def test_settings_shows_navigation_section(client):
    _setup(client)
    response = client.get("/settings", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert b"Navigation" in response.data


def test_edit_page_title_required(client):
    user, site = _setup(client)
    with app.app_context():
        create_page(site["id"], "about", "About")
    response = client.post(
        "/edit-page/about",
        data={"title": "", "body": "Some body"},
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    assert b"Title is required" in response.data
