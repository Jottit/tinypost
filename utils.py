import re

def is_valid_subdomain(name):
    return bool(re.match(r'^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$', name))

def slugify(text):
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return slug or None

def site_url(subdomain):
    from app import app
    return f"http://{subdomain}.{app.config['BASE_DOMAIN']}"
