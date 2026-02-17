import re


def is_valid_subdomain(name):
    return bool(re.match(r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", name))


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or None


def mask_email(email):
    local, domain = email.split("@")
    return local[:2] + "****@" + domain


def site_url(site):
    from app import app

    return f"http://{site['subdomain']}.{app.config['BASE_DOMAIN']}"
