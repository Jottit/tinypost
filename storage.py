import os
from pathlib import Path

from flask import current_app


def file_size(file):
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size


def upload_image(key, file, content_type):
    bucket = os.environ.get("BUCKET_NAME")
    if bucket:
        return _upload_to_s3(bucket, key, file, content_type)

    dest = Path(current_app.instance_path) / "uploads" / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file.read())
    return f"/uploads/{key}"


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
