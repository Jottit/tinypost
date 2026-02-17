import os

MAX_IMAGE_SIZE = 5 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

CADDY_ASK_TOKEN = os.environ.get("CADDY_ASK_TOKEN", "")
CUSTOM_DOMAIN_IPV4 = os.environ.get("CUSTOM_DOMAIN_IPV4", "")
CUSTOM_DOMAIN_IPV6 = os.environ.get("CUSTOM_DOMAIN_IPV6", "")
