import json
from unittest.mock import patch

from app import app
from db import create_post, create_user_and_site, get_post_by_slug
from indieauth_db import create_auth_code, exchange_auth_code


def make_site(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    return user, site


def make_token(site, scope="create"):
    with app.app_context():
        create_auth_code(site["id"], "testcode", "https://app.example.com",
                         "https://app.example.com/cb", scope, "challenge", "S256")
        exchange_auth_code("testcode", "test-access-token")
    return "test-access-token"


BASE = "http://myblog.jottit.localhost:8000"


class TestMicropubCreate:
    def test_create_post_form(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.post(
            "/micropub",
            data={"h": "entry", "name": "Hello World", "content": "This is my post."},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        assert "/hello-world" in resp.headers["Location"]
        with app.app_context():
            post = get_post_by_slug(site["id"], "hello-world")
            assert post["title"] == "Hello World"
            assert post["body"] == "This is my post."
            assert post["is_draft"] is False

    def test_create_post_json(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.post(
            "/micropub",
            data=json.dumps({
                "type": ["h-entry"],
                "properties": {
                    "name": ["JSON Post"],
                    "content": ["Body from JSON."],
                },
            }),
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        assert "/json-post" in resp.headers["Location"]

    def test_create_draft(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.post(
            "/micropub",
            data={"name": "Draft Post", "content": "WIP", "post-status": "draft"},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        with app.app_context():
            post = get_post_by_slug(site["id"], "draft-post")
            assert post["is_draft"] is True

    def test_create_untitled_post(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.post(
            "/micropub",
            data={"content": "Just a note."},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        assert resp.headers["Location"]

    def test_duplicate_slug_gets_suffix(self, client):
        _, site = make_site(client)
        token = make_token(site)
        with app.app_context():
            create_post(site["id"], "hello", "Hello", "First")
        resp = client.post(
            "/micropub",
            data={"name": "Hello", "content": "Second"},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        assert "/hello-" in resp.headers["Location"]
        assert resp.headers["Location"] != f"{BASE}/hello"


class TestMicropubAuth:
    def test_missing_token(self, client):
        make_site(client)
        resp = client.post("/micropub", data={"content": "test"}, base_url=BASE)
        assert resp.status_code == 401

    def test_invalid_token(self, client):
        make_site(client)
        resp = client.post(
            "/micropub",
            data={"content": "test"},
            headers={"Authorization": "Bearer bad-token"},
            base_url=BASE,
        )
        assert resp.status_code == 401

    def test_insufficient_scope(self, client):
        _, site = make_site(client)
        token = make_token(site, scope="profile")
        resp = client.post(
            "/micropub",
            data={"content": "test"},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 403


class TestMicropubQuery:
    def test_config(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.get(
            "/micropub?q=config",
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 200
        assert resp.get_json()["syndicate-to"] == []

    def test_syndicate_to(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.get(
            "/micropub?q=syndicate-to",
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 200
        assert resp.get_json()["syndicate-to"] == []

    def test_source(self, client):
        _, site = make_site(client)
        token = make_token(site)
        with app.app_context():
            create_post(site["id"], "my-post", "My Post", "The body")
        resp = client.get(
            f"/micropub?q=source&url={BASE}/my-post",
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["type"] == ["h-entry"]
        assert data["properties"]["name"] == ["My Post"]
        assert data["properties"]["content"] == ["The body"]

    def test_source_not_found(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.get(
            f"/micropub?q=source&url={BASE}/nonexistent",
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 400


class TestMicropubMedia:
    @patch("micropub.upload_image")
    def test_upload(self, mock_upload, client):
        _, site = make_site(client)
        token = make_token(site)
        mock_upload.return_value = "https://cdn.example.com/myblog/test.jpg"
        from io import BytesIO
        data = {"file": (BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100), "photo.jpg", "image/jpeg")}
        resp = client.post(
            "/micropub/media",
            data=data,
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        assert "Location" in resp.headers
        mock_upload.assert_called_once()

    def test_upload_no_file(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.post(
            "/micropub/media",
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 400

    def test_upload_bad_type(self, client):
        _, site = make_site(client)
        token = make_token(site)
        from io import BytesIO
        data = {"file": (BytesIO(b"not an image"), "file.txt", "text/plain")}
        resp = client.post(
            "/micropub/media",
            data=data,
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 400

    def test_upload_unauthorized(self, client):
        make_site(client)
        from io import BytesIO
        data = {"file": (BytesIO(b"\xff\xd8\xff\xe0"), "photo.jpg", "image/jpeg")}
        resp = client.post(
            "/micropub/media",
            data=data,
            content_type="multipart/form-data",
            base_url=BASE,
        )
        assert resp.status_code == 401
