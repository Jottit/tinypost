import html
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import markdown
from markupsafe import Markup

from appearance import get_appearance_vars
from utils import site_url, subdomain_url


def init_templates(app):
    @app.context_processor
    def inject_now():
        return {"now": datetime.now(timezone.utc)}

    @app.template_filter("markdown")
    def markdown_filter(text):
        return Markup(markdown.markdown(text))

    @app.template_filter("timeago")
    def timeago_filter(dt):
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        if days < 14:
            return f"{days} day{'s' if days != 1 else ''} ago"
        weeks = days // 7
        if weeks < 9:
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        months = days // 30
        if months < 12:
            return f"{months} month{'s' if months != 1 else ''} ago"
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"

    @app.template_filter("timeago_short")
    def timeago_short_filter(dt):
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h"
        days = hours // 24
        if days < 14:
            return f"{days}d"
        weeks = days // 7
        if weeks < 9:
            return f"{weeks}w"
        months = days // 30
        if months < 12:
            return f"{months}mo"
        years = days // 365
        return f"{years}y"

    @app.template_filter("avatar_color")
    def avatar_color_filter(name):
        colors = [
            "#7c5cbf",
            "#e67e22",
            "#e74c3c",
            "#3498db",
            "#1abc9c",
            "#9b59b6",
            "#2ecc71",
            "#e84393",
        ]
        return colors[sum(ord(c) for c in name) % len(colors)]

    @app.template_filter("initials")
    def initials_filter(name):
        if not name:
            return ""
        if name.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            name = urlparse(name).hostname or name
            name = name.removeprefix("www.")
        words = name.split()
        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()
        return name[0].upper()

    @app.template_filter("unescape")
    def unescape_filter(text):
        if not text:
            return text
        return html.unescape(text)

    @app.template_filter("autolink_label")
    def autolink_label_filter(label):
        if not label:
            return label
        if label.startswith(("http://", "https://")):
            host = urlparse(label).hostname or label
            return host.removeprefix("www.")
        return label

    _url_re = re.compile(
        r"(https?://[^\s<>\"')\]]+)"
        r"|"
        r"(?<![/@\w])(\b[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\."
        r"(?:com|org|net|io|co|dev|blog|me|info|xyz)\b(?:/[^\s<>\"')\]]*)?)"
    )

    @app.template_filter("autolink")
    def autolink_filter(text):
        if not text:
            return text
        escaped = Markup.escape(text)

        def replace_url(m):
            full_url = m.group(1)
            bare_domain = m.group(2)
            if full_url:
                url = full_url
                host = urlparse(str(url)).hostname or url
                label = host.removeprefix("www.")
            else:
                url = f"https://{bare_domain}"
                label = bare_domain
            return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'

        return Markup(_url_re.sub(replace_url, str(escaped)))

    @app.template_filter("nl2br")
    def nl2br_filter(text):
        return Markup(Markup.escape(text).replace("\n", Markup("<br>")))

    @app.template_filter("comment_markdown")
    def comment_markdown_filter(text):
        html = markdown.markdown(text)
        html = re.sub(r"<h[1-6][^>]*>|</h[1-6]>", "", html)
        html = re.sub(r"<img[^>]*/?>", "", html)
        return Markup(html)

    @app.template_filter("readtime")
    def readtime_filter(text):
        if not text:
            return "1 min read"
        words = len(text.split())
        minutes = max(1, round(words / 200))
        return f"{minutes} min read"

    @app.template_filter("truncatewords")
    def truncatewords_filter(text, n=50):
        words = text.split()
        if len(words) <= n:
            return text
        return " ".join(words[:n]) + "…"

    _img_re = re.compile(r"!\[[^\]]*\]\([^)]+\)")

    @app.template_filter("first_image")
    def first_image_filter(text):
        if not text:
            return ""
        m = _img_re.search(text)
        if not m:
            return ""
        md = m.group(0)
        url = md.split("](", 1)[1].rstrip(")")
        return url

    @app.template_filter("strip_first_image")
    def strip_first_image_filter(text):
        if not text:
            return text
        return _img_re.sub("", text, count=1).strip()

    @app.template_filter("plain_text")
    def plain_text_filter(text):
        if not text:
            return ""
        html = markdown.markdown(text)
        clean = re.sub(r"<[^>]+>", "", html)
        return re.sub(r"\s+", " ", clean).strip()

    app.jinja_env.globals["site_url"] = site_url
    app.jinja_env.globals["subdomain_url"] = subdomain_url
    app.jinja_env.globals["site_appearance_vars"] = get_appearance_vars
