import csv
import io
import zipfile
from unittest.mock import MagicMock, patch

from app import app
from db import create_post, create_user_and_site, get_post_by_slug

HOST = {"Host": "myblog.jottit.localhost:8000"}


def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def make_zip(csv_rows, html_files=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        out = io.StringIO()
        writer = csv.DictWriter(
            out,
            fieldnames=["post_id", "title", "slug", "post_date", "is_published"],
        )
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
        zf.writestr("posts.csv", out.getvalue())
        for name, content in (html_files or {}).items():
            zf.writestr(f"posts/{name}", content)
    buf.seek(0)
    return buf


def test_import_posts(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])

    archive = make_zip(
        [
            {
                "post_id": "1",
                "title": "Hello",
                "slug": "hello",
                "post_date": "2024-01-15T12:00:00Z",
                "is_published": "true",
            }
        ],
        {"1.html": "<h1>Hello</h1><p>World</p>"},
    )

    response = client.post(
        "/account/import",
        data={"archive": (archive, "export.zip")},
        headers=HOST,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"1 posts imported" in response.data

    with app.app_context():
        post = get_post_by_slug(site["id"], "hello")
        assert post is not None
        assert post["title"] == "Hello"
        assert post["published_at"] is not None


def test_import_skips_existing_slug(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "hello", "Existing", "existing body")
    login(client, user["id"])

    archive = make_zip(
        [
            {
                "post_id": "1",
                "title": "Hello",
                "slug": "hello",
                "post_date": "2024-01-15T12:00:00Z",
                "is_published": "true",
            }
        ],
        {"1.html": "<p>New body</p>"},
    )

    response = client.post(
        "/account/import",
        data={"archive": (archive, "export.zip")},
        headers=HOST,
        content_type="multipart/form-data",
    )
    assert b"1 skipped" in response.data

    with app.app_context():
        post = get_post_by_slug(site["id"], "hello")
        assert post["body"] == "existing body"


def test_import_skips_unpublished(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])

    archive = make_zip(
        [
            {
                "post_id": "1",
                "title": "Draft",
                "slug": "draft",
                "post_date": "2024-01-15T12:00:00Z",
                "is_published": "false",
            }
        ],
        {"1.html": "<p>Draft content</p>"},
    )

    response = client.post(
        "/account/import",
        data={"archive": (archive, "export.zip")},
        headers=HOST,
        content_type="multipart/form-data",
    )
    assert b"0 posts imported" in response.data

    with app.app_context():
        assert get_post_by_slug(site["id"], "draft") is None


def test_import_converts_html_to_markdown(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])

    archive = make_zip(
        [
            {
                "post_id": "1",
                "title": "Formatted",
                "slug": "formatted",
                "post_date": "2024-01-15T12:00:00Z",
                "is_published": "true",
            }
        ],
        {"1.html": "<p>Some <strong>bold</strong> and <em>italic</em> text.</p>"},
    )

    response = client.post(
        "/account/import",
        data={"archive": (archive, "export.zip")},
        headers=HOST,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200

    with app.app_context():
        post = get_post_by_slug(site["id"], "formatted")
        assert "**bold**" in post["body"]
        assert "*italic*" in post["body"]


def test_import_invalid_zip(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])

    response = client.post(
        "/account/import",
        data={"archive": (io.BytesIO(b"not a zip"), "bad.zip")},
        headers=HOST,
        content_type="multipart/form-data",
    )
    assert b"Invalid zip file" in response.data


def test_import_no_file(client):
    with app.app_context():
        user, _ = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])

    response = client.post("/account/import", headers=HOST)
    assert b"No file selected" in response.data


def test_import_multiple_posts(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
    login(client, user["id"])

    archive = make_zip(
        [
            {
                "post_id": "1",
                "title": "First",
                "slug": "first",
                "post_date": "2024-01-01T00:00:00Z",
                "is_published": "true",
            },
            {
                "post_id": "2",
                "title": "Second",
                "slug": "second",
                "post_date": "2024-02-01T00:00:00Z",
                "is_published": "true",
            },
        ],
        {"1.html": "<p>First post</p>", "2.html": "<p>Second post</p>"},
    )

    response = client.post(
        "/account/import",
        data={"archive": (archive, "export.zip")},
        headers=HOST,
        content_type="multipart/form-data",
    )
    assert b"2 posts imported" in response.data

    with app.app_context():
        assert get_post_by_slug(site["id"], "first") is not None
        assert get_post_by_slug(site["id"], "second") is not None


def _mock_urlopen(url):
    resp = MagicMock()
    resp.read.return_value = b"\x89PNG fake image"
    resp.headers = {"Content-Type": "image/png"}
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_rehost_substack_images(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(
            site["id"],
            "img-post",
            "Images",
            "![photo](https://substackcdn.com/image/fetch/w_800/photo.jpg)",
        )
    login(client, user["id"])

    archive = make_zip([], {})
    with patch("substack.urlopen", side_effect=_mock_urlopen):
        with patch("substack.upload_image", return_value="/uploads/myblog/new.png"):
            response = client.post(
                "/account/import",
                data={"archive": (archive, "export.zip")},
                headers=HOST,
                content_type="multipart/form-data",
            )

    assert b"1 images re-hosted" in response.data
    with app.app_context():
        post = get_post_by_slug(site["id"], "img-post")
        assert "substackcdn.com" not in post["body"]
        assert "/uploads/myblog/new.png" in post["body"]


def test_rehost_skips_non_substack_urls(client):
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(
            site["id"],
            "ext-post",
            "External",
            "![photo](https://example.com/photo.jpg)",
        )
    login(client, user["id"])

    archive = make_zip([], {})
    with patch("substack.urlopen", side_effect=_mock_urlopen):
        with patch("substack.upload_image", return_value="/uploads/myblog/new.png") as mock_upload:
            response = client.post(
                "/account/import",
                data={"archive": (archive, "export.zip")},
                headers=HOST,
                content_type="multipart/form-data",
            )

    mock_upload.assert_not_called()
    with app.app_context():
        post = get_post_by_slug(site["id"], "ext-post")
        assert "example.com/photo.jpg" in post["body"]


def test_rehost_deduplicates_same_url(client):
    url = "https://substack-post-media.s3.amazonaws.com/public/images/abc.jpg"
    with app.app_context():
        user, site = create_user_and_site("owner@example.com", "myblog")
        create_post(site["id"], "dup", "Dup", f"![a]({url}) ![b]({url})")
    login(client, user["id"])

    archive = make_zip([], {})
    with patch("substack.urlopen", side_effect=_mock_urlopen) as mock_fetch:
        with patch("substack.upload_image", return_value="/uploads/myblog/new.png"):
            client.post(
                "/account/import",
                data={"archive": (archive, "export.zip")},
                headers=HOST,
                content_type="multipart/form-data",
            )

    mock_fetch.assert_called_once()
    with app.app_context():
        post = get_post_by_slug(site["id"], "dup")
        assert post["body"].count("/uploads/myblog/new.png") == 2
