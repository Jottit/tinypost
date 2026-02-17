import os
import shutil
from io import BytesIO
from pathlib import Path

import boto3
from flask import current_app
from PIL import Image


def file_size(file):
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size


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
    bucket = os.environ.get("BUCKET_NAME")
    if bucket:
        return _upload_to_s3(bucket, key, file, content_type)

    dest = Path(current_app.instance_path) / "uploads" / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file.read())
    return f"/uploads/{key}"


def delete_image(key):
    bucket = os.environ.get("BUCKET_NAME")
    if bucket:
        return _delete_from_s3(bucket, key)

    dest = Path(current_app.instance_path) / "uploads" / key
    if dest.exists():
        dest.unlink()


def delete_all_images(subdomain):
    bucket = os.environ.get("BUCKET_NAME")
    if bucket:
        client = _s3_client()
        response = client.list_objects_v2(Bucket=bucket, Prefix=f"{subdomain}/")
        for obj in response.get("Contents", []):
            client.delete_object(Bucket=bucket, Key=obj["Key"])
        return

    uploads_dir = Path(current_app.instance_path) / "uploads" / subdomain
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir)


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("AWS_ENDPOINT_URL_S3"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )


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
