import re

RESERVED_SUBDOMAINS = {
    "www",
    "mail",
    "ftp",
    "admin",
    "api",
    "app",
    "smtp",
    "pop",
    "imap",
    "i",
    "m",
    "ns",
    "mx",
    "ww",
    "w",
}


def is_valid_subdomain(name):
    if name in RESERVED_SUBDOMAINS:
        return False
    return bool(re.match(r"^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$", name))


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or None


def mask_email(email):
    local, domain = email.split("@")
    return local[:2] + "****@" + domain


def auto_text_color(bg_hex):
    r, g, b = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#444444" if luminance > 0.5 else "#cccccc"


def site_url(site):
    if site.get("custom_domain") and site.get("domain_verified_at"):
        return f"https://{site['custom_domain']}"
    return subdomain_url(site)


def subdomain_url(site):
    from app import app

    return f"http://{site['subdomain']}.{app.config['BASE_DOMAIN']}"


def host_and_base():
    from flask import request

    from app import app

    host = request.host.split(":")[0]
    base = app.config["BASE_DOMAIN"].split(":")[0]
    return host, base


def get_current_site():
    from db import get_site_by_custom_domain, get_site_by_subdomain

    host, base = host_and_base()
    suffix = "." + base
    if host.endswith(suffix):
        subdomain = host.removesuffix(suffix)
        return get_site_by_subdomain(subdomain)
    if host != base:
        return get_site_by_custom_domain(host)
    return None
