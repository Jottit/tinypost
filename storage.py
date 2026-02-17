import os
from io import BytesIO
from pathlib import Path

from flask import current_app


def file_size(file):
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size


def crop_square(file, format):
    from PIL import Image

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


def _upload_to_s3(bucket, key, file, content_type):
    import boto3

    endpoint = os.environ.get("AWS_ENDPOINT_URL_S3")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
    client.upload_fileobj(
        file,
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    storage_url = os.environ.get("STORAGE_URL", f"https://{bucket}.fly.storage.tigris.dev")
    return f"{storage_url}/{key}"


def _delete_from_s3(bucket, key):
    import boto3

    endpoint = os.environ.get("AWS_ENDPOINT_URL_S3")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
    client.delete_object(Bucket=bucket, Key=key)
