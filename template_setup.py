import re
from datetime import datetime, timezone

import markdown
from markupsafe import Markup

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

    @app.template_filter("nl2br")
    def nl2br_filter(text):
        return Markup(Markup.escape(text).replace("\n", Markup("<br>")))

    @app.template_filter("comment_markdown")
    def comment_markdown_filter(text):
        html = markdown.markdown(text)
        html = re.sub(r"<h[1-6][^>]*>|</h[1-6]>", "", html)
        html = re.sub(r"<img[^>]*/?>", "", html)
        return Markup(html)

    @app.template_filter("truncatewords")
    def truncatewords_filter(text, n=50):
        words = text.split()
        if len(words) <= n:
            return text
        return " ".join(words[:n]) + "…"

    @app.template_filter("plain_text")
    def plain_text_filter(text):
        if not text:
            return ""
        html = markdown.markdown(text)
        clean = re.sub(r"<[^>]+>", "", html)
        return re.sub(r"\s+", " ", clean).strip()

    app.jinja_env.globals["site_url"] = site_url
    app.jinja_env.globals["subdomain_url"] = subdomain_url
