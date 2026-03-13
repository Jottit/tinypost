from io import BytesIO
from unittest.mock import patch

from app import app
from db import create_user

SITE_HOST = "myblog.tinypost.localhost:8000"


def _login(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]


def _make_image(content_type="image/png", size=1024, filename="test.png"):
    return (BytesIO(b"\x89PNG" + b"\x00" * size), filename, content_type)


def _post_upload(client, **data):
    return client.post(
        "/-/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Host": SITE_HOST},
    )


@patch("routes.uploads.upload_image", return_value="https://example.com/bucket/myblog/img.png")
def test_upload_success(mock_upload, client):
    _login(client)
    data, filename, content_type = _make_image()
    response = _post_upload(client, file=(data, filename, content_type))
    assert response.status_code == 200
    assert response.json["url"] == "https://example.com/bucket/myblog/img.png"
    mock_upload.assert_called_once()


def test_upload_requires_auth(client):
    with app.app_context():
        create_user("owner@example.com", "myblog")
    data, filename, content_type = _make_image()
    response = _post_upload(client, file=(data, filename, content_type))
    assert response.status_code == 401
    assert response.json["error"] == "Unauthorized"


@patch("routes.uploads.upload_image")
def test_upload_rejects_oversized(mock_upload, client):
    _login(client)
    data, filename, content_type = _make_image(size=6 * 1024 * 1024)
    response = _post_upload(client, file=(data, filename, content_type))
    assert response.status_code == 400
    assert "too large" in response.json["error"]
    mock_upload.assert_not_called()


@patch("routes.uploads.upload_image")
def test_upload_rejects_bad_type(mock_upload, client):
    _login(client)
    response = _post_upload(
        client, file=(BytesIO(b"%PDF-1.4 fake pdf"), "doc.pdf", "application/pdf")
    )
    assert response.status_code == 400
    assert "not allowed" in response.json["error"]
    mock_upload.assert_not_called()


@patch("routes.uploads.upload_image")
def test_upload_rejects_no_file(mock_upload, client):
    _login(client)
    response = _post_upload(client)
    assert response.status_code == 400
    assert "No file" in response.json["error"]
    mock_upload.assert_not_called()


def test_upload_404_no_site(client):
    response = client.post(
        "/-/upload",
        content_type="multipart/form-data",
    )
    assert response.status_code == 404
