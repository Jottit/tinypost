import os
import shutil
from io import BytesIO
from pathlib import Path

import boto3
from flask import current_app
from PIL import Image

from config import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE

BUCKET_NAME = os.environ.get("BUCKET_NAME")


def file_size(file):
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size


def validate_image(file):
    """Returns error message string, or None if valid."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return "File type not allowed"
    if file_size(file) > MAX_IMAGE_SIZE:
        return "File too large (max 5MB)"
    return None


def crop_square(file, format):
    img = Image.open(file)
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    buf = BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def upload_image(key, file, content_type):
    if BUCKET_NAME:
        return _upload_to_s3(BUCKET_NAME, key, file, content_type)

    dest = Path(current_app.instance_path) / "uploads" / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file.read())
    return f"/uploads/{key}"


def delete_image(key):
    if BUCKET_NAME:
        return _delete_from_s3(BUCKET_NAME, key)

    dest = Path(current_app.instance_path) / "uploads" / key
    if dest.exists():
        dest.unlink()


def delete_all_images(subdomain):
    if BUCKET_NAME:
        client = _s3_client()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=f"{subdomain}/"):
            for obj in page.get("Contents", []):
                client.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])
        return

    uploads_dir = Path(current_app.instance_path) / "uploads" / subdomain
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir)


_client = None


def _s3_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("AWS_ENDPOINT_URL_S3"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
    return _client


def _upload_to_s3(bucket, key, file, content_type):
    _s3_client().upload_fileobj(
        file,
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    storage_url = os.environ.get("STORAGE_URL", f"https://{bucket}.fly.storage.tigris.dev")
    return f"{storage_url}/{key}"


def _delete_from_s3(bucket, key):
    _s3_client().delete_object(Bucket=bucket, Key=key)


def list_images(subdomain):
    if BUCKET_NAME:
        return _list_from_s3(BUCKET_NAME, subdomain)

    upload_dir = Path(current_app.instance_path) / "uploads" / subdomain
    if not upload_dir.exists():
        return []
    return [f"{subdomain}/{f.name}" for f in upload_dir.iterdir() if f.is_file()]


def download_image(key):
    if BUCKET_NAME:
        return _download_from_s3(BUCKET_NAME, key)

    path = Path(current_app.instance_path) / "uploads" / key
    if not path.exists():
        return None
    return path.read_bytes()


def _list_from_s3(bucket, subdomain):
    paginator = _s3_client().get_paginator("list_objects_v2")
    return [
        obj["Key"]
        for page in paginator.paginate(Bucket=bucket, Prefix=f"{subdomain}/")
        for obj in page.get("Contents", [])
    ]


def _download_from_s3(bucket, key):
    buf = BytesIO()
    _s3_client().download_fileobj(bucket, key, buf)
    return buf.getvalue()
