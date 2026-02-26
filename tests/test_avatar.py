import json
import xml.etree.ElementTree as ET
from io import BytesIO
from unittest.mock import patch

from app import app
from db import create_user_and_site, update_site_avatar

SITE_HOST = "myblog.tinypost.localhost:8000"


def _login(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    return site


def _make_image(content_type="image/png", size=1024, filename="test.png"):
    return (BytesIO(b"\x89PNG" + b"\x00" * size), filename, content_type)


@patch("routes.settings.crop_square")
@patch("routes.settings.upload_image", return_value="https://example.com/myblog/avatar.png")
def test_upload_avatar(mock_upload, mock_crop, client):
    mock_crop.return_value = BytesIO(b"cropped")
    _login(client)
    data, filename, content_type = _make_image()
    response = client.post(
        "/-/settings/avatar",
        data={"avatar": (data, filename, content_type)},
        content_type="multipart/form-data",
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    assert "/-/settings" in response.headers["Location"]
    mock_crop.assert_called_once()
    mock_upload.assert_called_once()


@patch("routes.settings.crop_square")
@patch("routes.settings.upload_image")
def test_upload_avatar_rejects_bad_type(mock_upload, mock_crop, client):
    _login(client)
    response = client.post(
        "/-/settings/avatar",
        data={"avatar": (BytesIO(b"%PDF"), "doc.pdf", "application/pdf")},
        content_type="multipart/form-data",
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    assert b"not allowed" in response.data
    mock_upload.assert_not_called()


@patch("routes.settings.crop_square")
@patch("routes.settings.upload_image")
def test_upload_avatar_rejects_oversized(mock_upload, mock_crop, client):
    _login(client)
    data, filename, content_type = _make_image(size=6 * 1024 * 1024)
    response = client.post(
        "/-/settings/avatar",
        data={"avatar": (data, filename, content_type)},
        content_type="multipart/form-data",
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 200
    assert b"too large" in response.data
    mock_upload.assert_not_called()


@patch("routes.settings.delete_image")
def test_remove_avatar(mock_delete, client):
    site = _login(client)
    with app.app_context():
        update_site_avatar(site["id"], "/uploads/myblog/avatar.png")
    response = client.post(
        "/-/settings/avatar/delete",
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    assert "/-/settings" in response.headers["Location"]
    mock_delete.assert_called_once_with("myblog/avatar.png")


def test_upload_avatar_requires_auth(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.post(
        "/-/settings/avatar",
        data={"avatar": _make_image()},
        content_type="multipart/form-data",
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_delete_avatar_requires_auth(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.post(
        "/-/settings/avatar/delete",
        headers={"Host": SITE_HOST},
    )
    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_rss_feed_includes_avatar(client):
    with app.app_context():
        _, site = create_user_and_site("owner@example.com", "myblog")
        update_site_avatar(site["id"], "https://example.com/myblog/avatar.png")
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    root = ET.fromstring(response.data)
    image = root.find("channel/image")
    assert image is not None
    assert image.find("url").text == "https://example.com/myblog/avatar.png"
    assert image.find("title").text == "myblog"


def test_rss_feed_no_image_without_avatar(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get("/feed.xml", headers={"Host": SITE_HOST})
    root = ET.fromstring(response.data)
    image = root.find("channel/image")
    assert image is None


def test_json_feed_includes_avatar(client):
    with app.app_context():
        _, site = create_user_and_site("owner@example.com", "myblog")
        update_site_avatar(site["id"], "https://example.com/myblog/avatar.png")
    response = client.get("/feed.json", headers={"Host": SITE_HOST})
    data = json.loads(response.data)
    assert data["icon"] == "https://example.com/myblog/avatar.png"


def test_json_feed_no_icon_without_avatar(client):
    with app.app_context():
        create_user_and_site("owner@example.com", "myblog")
    response = client.get("/feed.json", headers={"Host": SITE_HOST})
    data = json.loads(response.data)
    assert "icon" not in data
