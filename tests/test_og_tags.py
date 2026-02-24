from app import app
from db import (
    create_page,
    create_post,
    create_user_and_site,
    update_page,
    update_site,
    update_site_avatar,
)

SITE_HOST = "myblog.jottit.localhost:8000"


def _setup(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess.clear()
    return user, site


def test_plain_text_filter_strips_markdown():
    with app.app_context():
        tmpl = app.jinja_env.from_string("{{ text|plain_text }}")
        result = tmpl.render(text="**bold** and *italic*")
    assert result == "bold and italic"


def test_plain_text_filter_handles_empty():
    with app.app_context():
        tmpl = app.jinja_env.from_string("{{ text|plain_text }}")
        assert tmpl.render(text="") == ""
        assert tmpl.render(text=None) == ""


def test_post_og_tags(client):
    _, site = _setup(client)
    with app.app_context():
        update_site_avatar(site["id"], "https://example.com/avatar.jpg")
        create_post(site["id"], "hello", "Hello World", "This is my **first** post.")
    response = client.get("/hello", headers={"Host": SITE_HOST})
    html = response.data.decode()
    assert '<meta property="og:title" content="Hello World">' in html
    assert '<meta property="og:type" content="article">' in html
    assert '<meta property="og:url" content="http://myblog.jottit.localhost:8000/hello">' in html
    assert '<meta property="og:description" content="This is my first post.">' in html
    assert '<meta property="og:image" content="https://example.com/avatar.jpg">' in html
    assert '<meta name="twitter:card" content="summary">' in html
    assert '<meta name="twitter:title" content="Hello World">' in html


def test_page_og_tags(client):
    _, site = _setup(client)
    with app.app_context():
        page = create_page(site["id"], "about", "About Me")
        update_page(page["id"], "About Me", "All about me.", is_draft=False)
    response = client.get("/about", headers={"Host": SITE_HOST})
    html = response.data.decode()
    assert '<meta property="og:title" content="About Me">' in html
    assert '<meta property="og:type" content="website">' in html
    assert '<meta property="og:url" content="http://myblog.jottit.localhost:8000/about">' in html


def test_site_homepage_og_tags(client):
    _, site = _setup(client)
    with app.app_context():
        update_site(site["id"], "My Blog", "A blog about things")
    response = client.get("/", headers={"Host": SITE_HOST})
    html = response.data.decode()
    assert '<meta property="og:title" content="My Blog">' in html
    assert '<meta property="og:type" content="website">' in html
    assert '<meta property="og:url" content="http://myblog.jottit.localhost:8000">' in html
    assert '<meta property="og:description" content="A blog about things">' in html
    assert '<meta property="og:site_name" content="My Blog">' in html


def test_description_falls_back_to_bio(client):
    _, site = _setup(client)
    with app.app_context():
        update_site(site["id"], "My Blog", "My site bio")
        create_post(site["id"], "hello", "Hello", "")
    response = client.get("/hello", headers={"Host": SITE_HOST})
    html = response.data.decode()
    assert '<meta property="og:description" content="My site bio">' in html


def test_og_image_omitted_without_avatar(client):
    _, site = _setup(client)
    with app.app_context():
        create_post(site["id"], "hello", "Hello", "Some content")
    response = client.get("/hello", headers={"Host": SITE_HOST})
    html = response.data.decode()
    assert "og:image" not in html
    assert "twitter:image" not in html


def test_description_truncated(client):
    _, site = _setup(client)
    long_body = "Word " * 100
    with app.app_context():
        create_post(site["id"], "hello", "Hello", long_body)
    response = client.get("/hello", headers={"Host": SITE_HOST})
    html = response.data.decode()
    for line in html.split("\n"):
        if "og:description" in line:
            content = line.split('content="')[1].split('"')[0]
            assert len(content) <= 160
            assert content.endswith("…")
            break
    else:
        raise AssertionError("og:description not found")
