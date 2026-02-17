from app import app
from db import create_user_and_site, get_site_by_subdomain, update_site_design


def test_design_requires_auth(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get("/design", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_design_get(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/design", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert b"Design" in response.data


def test_design_save(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/design",
        data={
            "font_header": "Georgia, serif",
            "font_body": "Verdana, sans-serif",
            "color_accent": "#117a65",
        },
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    d = updated["design"]
    assert d["font_header"] == "Georgia, serif"
    assert d["font_body"] == "Verdana, sans-serif"
    assert d["color_accent"] == "#117a65"


def test_design_rejects_invalid_color(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/design",
        data={"color_accent": "notacolor"},
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 200
    assert b"Invalid" in response.data


def test_design_rejects_invalid_font(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/design",
        data={"font_header": "Comic Sans MS"},
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["design"] is None


def test_design_applied_to_site(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site_design(site["id"], {"font_header": "Georgia, serif", "color_accent": "#117a65"})
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert b"--site-font-header: Georgia, serif" in response.data
    assert b"--site-accent: #117a65" in response.data


def test_design_empty_values_save_as_null(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site_design(site["id"], {"font_header": "Georgia, serif", "color_accent": "#117a65"})
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/design",
        data={"font_header": "", "color_accent": ""},
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["design"] is None


def test_design_bg_auto_derives_text(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/design",
        data={"color_bg": "#1a1a2e"},
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    d = updated["design"]
    assert d["color_bg"] == "#1a1a2e"
    assert d["color_text"] == "#cccccc"


def test_design_bg_with_custom_text(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/design",
        data={"color_bg": "#1a1a2e", "color_text": "#e0e0e0"},
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    d = updated["design"]
    assert d["color_text"] == "#e0e0e0"


def test_design_bg_applied_to_site(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site_design(site["id"], {"color_bg": "#1a1a2e", "color_text": "#cccccc"})
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.get("/", headers={"Host": "myblog.jottit.localhost:8000"})
    assert response.status_code == 200
    assert b"--site-bg: #1a1a2e" in response.data
    assert b"--site-text: #cccccc" in response.data


def test_design_clearing_bg_clears_text(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        update_site_design(site["id"], {"color_bg": "#1a1a2e", "color_text": "#cccccc"})
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    response = client.post(
        "/design",
        data={"color_bg": ""},
        headers={"Host": "myblog.jottit.localhost:8000"},
    )
    assert response.status_code == 302
    with app.app_context():
        updated = get_site_by_subdomain("myblog")
    assert updated["design"] is None
