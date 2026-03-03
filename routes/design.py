import os
import re

from flask import Response, flash, redirect, render_template, request

from app import app
from config import COLOR_RE, FONT_OPTIONS, VALID_FONT_VALUES
from db import update_site_custom_css, update_site_design
from routes import require_owner
from utils import auto_text_color, site_url


def sanitize_css(css):
    css = re.sub(r"<\s*/\s*style", "", css, flags=re.IGNORECASE)
    css = re.sub(r"@import\b[^;]*;?", "", css, flags=re.IGNORECASE)
    css = re.sub(r"expression\s*\(", "(", css, flags=re.IGNORECASE)
    css = re.sub(r"javascript\s*:", "", css, flags=re.IGNORECASE)
    css = re.sub(r"behavior\s*:", "", css, flags=re.IGNORECASE)
    css = re.sub(r"-moz-binding\s*:", "", css, flags=re.IGNORECASE)
    return css


@app.route("/-/design", methods=["GET", "POST"])
def design():
    site = require_owner()
    d = site["design"] or {}

    if request.method == "GET":
        return render_template(
            "design.html",
            site=site,
            is_owner=True,
            design=d,
            font_options=FONT_OPTIONS,
        )

    font_header = request.form.get("font_header", "").strip()
    font_body = request.form.get("font_body", "").strip()
    color_accent = request.form.get("color_accent", "").strip()
    color_bg = request.form.get("color_bg", "").strip()
    color_text = request.form.get("color_text", "").strip()

    if font_header not in VALID_FONT_VALUES:
        font_header = ""
    if font_body not in VALID_FONT_VALUES:
        font_body = ""

    for c in (color_accent, color_bg, color_text):
        if c and not COLOR_RE.match(c):
            return render_template(
                "design.html",
                site=site,
                is_owner=True,
                design=d,
                font_options=FONT_OPTIONS,
                error="Invalid color value.",
            )

    if color_bg and not color_text:
        color_text = auto_text_color(color_bg)
    if not color_bg:
        color_text = ""

    fields = {
        "font_header": font_header,
        "font_body": font_body,
        "color_accent": color_accent,
        "color_bg": color_bg,
        "color_text": color_text,
    }
    design_data = {k: v for k, v in fields.items() if v}
    update_site_design(site["id"], design_data or None)
    if request.headers.get("X-Auto-Save"):
        return "", 204
    flash("Design updated.")
    return redirect("/-/design")


@app.route("/-/download-theme")
def download_theme():
    site = require_owner()
    custom_css = site.get("custom_css")

    header = f"""\
/*
 * Theme: {"Custom" if custom_css else "Default"}
 * Author: {site["title"]}
 * Site: {site_url(site)}
 * Version: 1.0
 * License: {site.get("license") or ""}
 */

"""

    if not custom_css:
        theme_path = os.path.join(app.static_folder, "theme.css")
        with open(theme_path) as f:
            custom_css = f.read()

    return Response(
        header + custom_css,
        mimetype="text/css",
        headers={"Content-Disposition": 'attachment; filename="theme.css"'},
    )


@app.route("/-/design/upload-css", methods=["POST"])
def upload_css():
    site = require_owner()

    css_file = request.files.get("css_file")
    if not css_file:
        return redirect("/-/design")

    content = css_file.read().decode("utf-8", errors="replace").strip()
    if not content:
        return redirect("/-/design")

    content = sanitize_css(content)
    update_site_custom_css(site["id"], content)
    return redirect("/-/design")


@app.route("/-/design/remove-css", methods=["POST"])
def remove_css():
    site = require_owner()
    update_site_custom_css(site["id"], None)
    return redirect("/-/design")
