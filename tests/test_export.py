import zipfile
from io import BytesIO
from unittest.mock import patch

from app import app
from db import create_post, create_user_and_site

SITE_HOST = "myblog.jottit.localhost:8000"


def _login(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    return user, site


def _get_zip(response):
    return zipfile.ZipFile(BytesIO(response.data))


def test_export_requires_auth(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get("/-/settings/export", headers={"Host": SITE_HOST})
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_export_contains_published_posts(client):
    user, site = _login(client)
    with app.app_context():
        create_post(site["id"], "hello-world", "Hello World", "This is my first post.")
        create_post(site["id"], "second", "Second Post", "Another post.")
    response = client.get("/-/settings/export", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    assert response.content_type == "application/zip"
    zf = _get_zip(response)
    assert "hello-world.md" in zf.namelist()
    assert "second.md" in zf.namelist()


def test_export_drafts_in_subfolder(client):
    user, site = _login(client)
    with app.app_context():
        create_post(site["id"], "published", "Published", "Public post.")
        create_post(site["id"], "my-draft", "My Draft", "Draft content.", is_draft=True)
    response = client.get("/-/settings/export", headers={"Host": SITE_HOST})
    zf = _get_zip(response)
    assert "published.md" in zf.namelist()
    assert "drafts/my-draft.md" in zf.namelist()


def test_export_markdown_has_title_and_body(client):
    user, site = _login(client)
    with app.app_context():
        create_post(site["id"], "titled", "My Title", "Body text here.")
    response = client.get("/-/settings/export", headers={"Host": SITE_HOST})
    zf = _get_zip(response)
    content = zf.read("titled.md").decode()
    assert content == "# My Title\n\nBody text here."


@patch("routes.settings.list_images", return_value=["myblog/photo.png"])
@patch("routes.settings.download_image", return_value=b"\x89PNG fake image data")
def test_export_contains_images(mock_download, mock_list, client):
    _login(client)
    response = client.get("/-/settings/export", headers={"Host": SITE_HOST})
    zf = _get_zip(response)
    assert "images/photo.png" in zf.namelist()
    assert zf.read("images/photo.png") == b"\x89PNG fake image data"


def test_export_empty_site(client):
    _login(client)
    response = client.get("/-/settings/export", headers={"Host": SITE_HOST})
    assert response.status_code == 200
    zf = _get_zip(response)
    assert zf.namelist() == []
