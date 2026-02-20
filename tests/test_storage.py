from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app import app
from storage import (
    crop_square,
    delete_all_images,
    delete_image,
    download_image,
    file_size,
    list_images,
    upload_image,
)


def _make_image(width, height):
    img = Image.new("RGB", (width, height))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_file_size():
    f = BytesIO(b"x" * 100)
    assert file_size(f) == 100
    assert f.tell() == 0


def test_file_size_after_partial_read():
    f = BytesIO(b"x" * 200)
    f.read(50)
    assert file_size(f) == 200
    assert f.tell() == 0


def test_crop_square_landscape():
    result = crop_square(_make_image(200, 100), "PNG")
    assert Image.open(result).size == (100, 100)


def test_crop_square_portrait():
    result = crop_square(_make_image(100, 200), "PNG")
    assert Image.open(result).size == (100, 100)


def test_crop_square_already_square():
    result = crop_square(_make_image(100, 100), "PNG")
    assert Image.open(result).size == (100, 100)


def test_upload_image_local(client):
    with app.app_context():
        url = upload_image("myblog/test.png", BytesIO(b"fake image"), "image/png")
    assert url == "/uploads/myblog/test.png"
    dest = Path(app.instance_path) / "uploads" / "myblog" / "test.png"
    assert dest.read_bytes() == b"fake image"
    dest.unlink()


@patch("storage._s3_client")
def test_upload_image_s3(mock_client_fn):
    mock_s3 = MagicMock()
    mock_client_fn.return_value = mock_s3
    file = BytesIO(b"image data")

    with patch.dict(
        "os.environ", {"BUCKET_NAME": "my-bucket", "STORAGE_URL": "https://cdn.example.com"}
    ):
        url = upload_image("myblog/img.png", file, "image/png")

    assert url == "https://cdn.example.com/myblog/img.png"
    mock_s3.upload_fileobj.assert_called_once_with(
        file,
        "my-bucket",
        "myblog/img.png",
        ExtraArgs={"ContentType": "image/png"},
    )


@patch("storage._s3_client")
def test_upload_image_s3_default_url(mock_client_fn):
    mock_client_fn.return_value = MagicMock()

    env = {"BUCKET_NAME": "my-bucket"}
    with patch.dict("os.environ", env, clear=True):
        url = upload_image("myblog/img.png", BytesIO(b"data"), "image/png")

    assert url == "https://my-bucket.fly.storage.tigris.dev/myblog/img.png"


def test_delete_image_local(client):
    with app.app_context():
        dest = Path(app.instance_path) / "uploads" / "myblog" / "del.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"to delete")
        delete_image("myblog/del.png")
        assert not dest.exists()


def test_delete_image_local_missing(client):
    with app.app_context():
        delete_image("myblog/nonexistent.png")


@patch("storage._s3_client")
def test_delete_image_s3(mock_client_fn):
    mock_s3 = MagicMock()
    mock_client_fn.return_value = mock_s3

    with patch.dict("os.environ", {"BUCKET_NAME": "my-bucket"}):
        delete_image("myblog/img.png")

    mock_s3.delete_object.assert_called_once_with(Bucket="my-bucket", Key="myblog/img.png")


def test_delete_all_images_local(client):
    with app.app_context():
        uploads = Path(app.instance_path) / "uploads" / "testsite"
        uploads.mkdir(parents=True, exist_ok=True)
        (uploads / "a.png").write_bytes(b"a")
        (uploads / "b.png").write_bytes(b"b")
        delete_all_images("testsite")
        assert not uploads.exists()


def test_delete_all_images_local_missing_dir(client):
    with app.app_context():
        delete_all_images("nonexistent")


@patch("storage._s3_client")
def test_delete_all_images_s3(mock_client_fn):
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "site/a.png"}, {"Key": "site/b.png"}]
    }
    mock_client_fn.return_value = mock_s3

    with patch.dict("os.environ", {"BUCKET_NAME": "my-bucket"}):
        delete_all_images("site")

    mock_s3.list_objects_v2.assert_called_once_with(Bucket="my-bucket", Prefix="site/")
    assert mock_s3.delete_object.call_count == 2
    mock_s3.delete_object.assert_any_call(Bucket="my-bucket", Key="site/a.png")
    mock_s3.delete_object.assert_any_call(Bucket="my-bucket", Key="site/b.png")


@patch("storage._s3_client")
def test_delete_all_images_s3_empty(mock_client_fn):
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {}
    mock_client_fn.return_value = mock_s3

    with patch.dict("os.environ", {"BUCKET_NAME": "my-bucket"}):
        delete_all_images("site")

    mock_s3.delete_object.assert_not_called()


def test_list_images_local(client):
    with app.app_context():
        uploads = Path(app.instance_path) / "uploads" / "listsite"
        uploads.mkdir(parents=True, exist_ok=True)
        (uploads / "a.png").write_bytes(b"a")
        (uploads / "b.jpg").write_bytes(b"b")
        result = list_images("listsite")
        assert sorted(result) == ["listsite/a.png", "listsite/b.jpg"]
        (uploads / "a.png").unlink()
        (uploads / "b.jpg").unlink()
        uploads.rmdir()


def test_list_images_local_missing_dir(client):
    with app.app_context():
        assert list_images("nodir") == []


@patch("storage._s3_client")
def test_list_images_s3(mock_client_fn):
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": "site/a.png"}, {"Key": "site/b.jpg"}]},
    ]
    mock_s3.get_paginator.return_value = mock_paginator
    mock_client_fn.return_value = mock_s3

    with patch.dict("os.environ", {"BUCKET_NAME": "my-bucket"}):
        result = list_images("site")

    assert result == ["site/a.png", "site/b.jpg"]
    mock_paginator.paginate.assert_called_once_with(Bucket="my-bucket", Prefix="site/")


def test_download_image_local(client):
    with app.app_context():
        dest = Path(app.instance_path) / "uploads" / "dl" / "pic.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"image bytes")
        result = download_image("dl/pic.png")
        assert result == b"image bytes"
        dest.unlink()
        dest.parent.rmdir()


def test_download_image_local_missing(client):
    with app.app_context():
        assert download_image("dl/nope.png") is None


@patch("storage._s3_client")
def test_download_image_s3(mock_client_fn):
    mock_s3 = MagicMock()

    def fake_download(bucket, key, buf):
        buf.write(b"s3 data")

    mock_s3.download_fileobj.side_effect = fake_download
    mock_client_fn.return_value = mock_s3

    with patch.dict("os.environ", {"BUCKET_NAME": "my-bucket"}):
        result = download_image("site/pic.png")

    assert result == b"s3 data"
    mock_s3.download_fileobj.assert_called_once()


@patch("storage._s3_client")
def test_upload_s3_error(mock_client_fn):
    mock_s3 = MagicMock()
    mock_s3.upload_fileobj.side_effect = Exception("connection refused")
    mock_client_fn.return_value = mock_s3

    with patch.dict("os.environ", {"BUCKET_NAME": "my-bucket"}):
        with pytest.raises(Exception, match="connection refused"):
            upload_image("myblog/img.png", BytesIO(b"data"), "image/png")


@patch("storage._s3_client")
def test_delete_s3_error(mock_client_fn):
    mock_s3 = MagicMock()
    mock_s3.delete_object.side_effect = Exception("timeout")
    mock_client_fn.return_value = mock_s3

    with patch.dict("os.environ", {"BUCKET_NAME": "my-bucket"}):
        with pytest.raises(Exception, match="timeout"):
            delete_image("myblog/img.png")
