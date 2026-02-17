import os
import re

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

FONT_OPTIONS = [
    ("System Default", ""),
    ("Georgia", "Georgia, serif"),
    ("Palatino", '"Palatino Linotype", Palatino, serif'),
    ("Charter", "Charter, serif"),
    ("Garamond", "Garamond, serif"),
    ("Helvetica Neue", '"Helvetica Neue", Helvetica, sans-serif'),
    ("Verdana", "Verdana, sans-serif"),
    ("Trebuchet MS", '"Trebuchet MS", sans-serif'),
    ("Courier New", '"Courier New", Courier, monospace'),
]

COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
VALID_FONT_VALUES = {v for _, v in FONT_OPTIONS}
