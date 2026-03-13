import os
import uuid

from flask import abort, jsonify, request, send_from_directory, session

from app import app
from config import ALLOWED_IMAGE_TYPES
from storage import upload_image, validate_image
from utils import get_current_site


@app.route("/-/upload", methods=["POST"])
def upload():
    site = get_current_site()
    if not site:
        abort(404)
    if session.get("user_id") != site["id"]:
        return jsonify({"error": "Unauthorized"}), 401

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    error = validate_image(file)
    if error:
        return jsonify({"error": error}), 400

    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    key = f"{site['subdomain']}/{uuid.uuid4()}.{ext}"

    url = upload_image(key, file, file.content_type)
    return jsonify({"url": url})


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.instance_path, "uploads"), filename)
