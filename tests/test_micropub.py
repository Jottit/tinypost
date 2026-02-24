import json
from unittest.mock import patch

from app import app
from db import create_post, create_user_and_site, get_post_by_slug
from indieauth_db import (
    create_auth_code,
    create_personal_token,
    exchange_auth_code,
    get_personal_token,
    revoke_personal_token,
)


def make_site(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    return user, site


def make_token(site, scope="create"):
    with app.app_context():
        create_auth_code(
            site["id"],
            "testcode",
            "https://app.example.com",
            "https://app.example.com/cb",
            scope,
            "challenge",
            "S256",
        )
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
            data=json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "name": ["JSON Post"],
                        "content": ["Body from JSON."],
                    },
                }
            ),
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

    def test_create_with_mp_slug(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.post(
            "/micropub",
            data={"name": "My Title", "content": "Body", "mp-slug": "custom-slug"},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        assert "/custom-slug" in resp.headers["Location"]

    def test_extract_title_from_markdown_heading(self, client):
        _, site = make_site(client)
        token = make_token(site)
        resp = client.post(
            "/micropub",
            data={"content": "# Yo\n\nSome text"},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        assert "/yo" in resp.headers["Location"]
        with app.app_context():
            post = get_post_by_slug(site["id"], "yo")
            assert post["title"] == "Yo"
            assert post["body"] == "Some text"

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


class TestPersonalToken:
    def test_create_and_use_personal_token(self, client):
        _, site = make_site(client)
        with app.app_context():
            token = create_personal_token(site["id"])
            assert token
            row = get_personal_token(site["id"])
            assert row["token"] == token
            assert row["client_id"] == "personal-token"
            assert row["scope"] == "create"

        resp = client.post(
            "/micropub",
            data={"name": "Token Post", "content": "Via personal token."},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 201
        assert "/token-post" in resp.headers["Location"]

    def test_revoke_personal_token(self, client):
        _, site = make_site(client)
        with app.app_context():
            token = create_personal_token(site["id"])
            revoke_personal_token(site["id"])
            assert get_personal_token(site["id"]) is None

        resp = client.post(
            "/micropub",
            data={"content": "Should fail."},
            headers={"Authorization": f"Bearer {token}"},
            base_url=BASE,
        )
        assert resp.status_code == 401

    def test_create_replaces_existing_token(self, client):
        _, site = make_site(client)
        with app.app_context():
            token1 = create_personal_token(site["id"])
            token2 = create_personal_token(site["id"])
            assert token1 != token2
            assert get_personal_token(site["id"])["token"] == token2

    def test_account_token_route(self, client):
        user, site = make_site(client)
        with client.session_transaction() as sess:
            sess["user_id"] = user["id"]
        resp = client.post("/-/account/token", base_url=BASE)
        assert resp.status_code == 200
        assert b"Token created" in resp.data
        with app.app_context():
            assert get_personal_token(site["id"]) is not None

    def test_account_token_revoke_route(self, client):
        user, site = make_site(client)
        with app.app_context():
            create_personal_token(site["id"])
        with client.session_transaction() as sess:
            sess["user_id"] = user["id"]
        resp = client.post("/-/account/token/revoke", base_url=BASE, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert get_personal_token(site["id"]) is None
