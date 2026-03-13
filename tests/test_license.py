from app import app
from db import create_post, create_user, get_user_by_subdomain, update_user_blog

HOST = {"Host": "myblog.tinypost.localhost:8000"}


def setup_site(client=None):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    if client:
        with client.session_transaction() as sess:
            sess["user_id"] = user["id"]
    return user


def test_license_default_is_none(client):
    user = setup_site()
    assert user["license"] is None


def test_set_license_in_settings(client):
    setup_site(client)
    client.post(
        "/-/settings/license",
        data={"license": "cc-by-4.0"},
        headers=HOST,
    )
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert updated["license"] == "cc-by-4.0"


def test_clear_license(client):
    setup_site(client)
    client.post(
        "/-/settings/license",
        data={"license": "cc-by-4.0"},
        headers=HOST,
    )
    client.post(
        "/-/settings/license",
        data={"license": ""},
        headers=HOST,
    )
    with app.app_context():
        updated = get_user_by_subdomain("myblog")
    assert updated["license"] is None


def test_license_shown_in_settings_form(client):
    setup_site(client)
    client.post(
        "/-/settings/license",
        data={"license": "cc-by-nc-4.0"},
        headers=HOST,
    )
    response = client.get("/-/settings/license", headers=HOST)
    assert b'value="cc-by-nc-4.0" selected' in response.data


def test_cc_license_in_footer(client):
    user = setup_site()
    with app.app_context():
        update_user_blog(user["id"], "My Blog", None, license="cc-by-4.0")
        create_post(user["id"], "hello", "Hello", "World")
    response = client.get("/", headers=HOST)
    assert b"CC BY 4.0" in response.data
    assert b"creativecommons.org/licenses/by/4.0/" in response.data


def test_all_rights_reserved_in_footer(client):
    user = setup_site()
    with app.app_context():
        update_user_blog(user["id"], "My Blog", None, license="all-rights-reserved")
        create_post(user["id"], "hello", "Hello", "World")
    response = client.get("/", headers=HOST)
    assert b"My Blog" in response.data
    assert b"&copy;" in response.data


def test_cc0_in_footer(client):
    user = setup_site()
    with app.app_context():
        update_user_blog(user["id"], "My Blog", None, license="cc0-1.0")
        create_post(user["id"], "hello", "Hello", "World")
    response = client.get("/", headers=HOST)
    assert b"CC0 1.0" in response.data
    assert b"creativecommons.org/publicdomain/zero/1.0/" in response.data


def test_no_license_no_footer_text(client):
    user = setup_site()
    with app.app_context():
        create_post(user["id"], "hello", "Hello", "World")
    response = client.get("/", headers=HOST)
    assert b"creativecommons.org" not in response.data
    assert b"All Rights Reserved" not in response.data
