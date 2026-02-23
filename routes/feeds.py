import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import format_datetime

import markdown as md
from flask import Response, abort, jsonify

from app import app
from db import get_blogroll, get_posts_for_site
from utils import get_current_site, site_url

CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
SOURCE_NS = "http://source.scripting.com/"
ET.register_namespace("content", CONTENT_NS)
ET.register_namespace("source", SOURCE_NS)


@app.route("/blogroll.opml")
def blogroll_opml():
    site = get_current_site()
    if not site:
        abort(404)
    items = get_blogroll(site["id"])

    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = f"{site['title']} Blogroll"
    body = ET.SubElement(opml, "body")
    for item in items:
        attrs = {"text": item["name"], "htmlUrl": item["url"], "type": "rss"}
        if item.get("feed_url"):
            attrs["xmlUrl"] = item["feed_url"]
        ET.SubElement(body, "outline", **attrs)

    xml_str = ET.tostring(opml, encoding="unicode", xml_declaration=False)
    xml_out = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    return Response(xml_out, content_type="text/x-opml; charset=utf-8")


@app.route("/feed.xml")
def feed():
    site = get_current_site()
    if not site:
        abort(404)
    posts = get_posts_for_site(site["id"])[:20]
    base_url = site_url(site)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = site["title"]
    ET.SubElement(channel, "link").text = base_url
    ET.SubElement(channel, "description").text = site["bio"] or site["title"]
    if site["avatar"]:
        image = ET.SubElement(channel, "image")
        ET.SubElement(image, "url").text = site["avatar"]
        ET.SubElement(image, "title").text = site["title"]
        ET.SubElement(image, "link").text = base_url
    if posts:
        last_build = (posts[0]["published_at"] or posts[0]["created_at"]).replace(
            tzinfo=timezone.utc
        )
        ET.SubElement(channel, "lastBuildDate").text = format_datetime(last_build)
    if get_blogroll(site["id"]):
        ET.SubElement(channel, f"{{{SOURCE_NS}}}blogroll").text = f"{base_url}/blogroll.opml"

    for p in posts:
        item = ET.SubElement(channel, "item")
        permalink = f"{base_url}/{p['slug']}"
        ET.SubElement(item, "title").text = p["title"] or ""
        ET.SubElement(item, "link").text = permalink
        ET.SubElement(item, "guid").text = permalink
        pub_date = (p["published_at"] or p["created_at"]).replace(tzinfo=timezone.utc)
        ET.SubElement(item, "pubDate").text = format_datetime(pub_date)
        html = md.markdown(p["body"])
        ET.SubElement(item, "description").text = html
        ET.SubElement(item, f"{{{CONTENT_NS}}}encoded").text = html
        ET.SubElement(item, f"{{{SOURCE_NS}}}markdown").text = p["body"]

    xml_str = ET.tostring(rss, encoding="unicode", xml_declaration=False)
    xml_out = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    return Response(xml_out, content_type="application/rss+xml; charset=utf-8")


@app.route("/feed.json")
def feed_json():
    site = get_current_site()
    if not site:
        abort(404)
    posts = get_posts_for_site(site["id"])[:20]
    base_url = site_url(site)

    items = []
    for p in posts:
        permalink = f"{base_url}/{p['slug']}"
        items.append(
            {
                "id": permalink,
                "url": permalink,
                "title": p["title"] or "",
                "content_html": md.markdown(p["body"]),
                "content_text": p["body"],
                "date_published": (p["published_at"] or p["created_at"])
                .replace(tzinfo=timezone.utc)
                .isoformat(),
            }
        )

    data = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": site["title"],
        "home_page_url": base_url,
        "feed_url": f"{base_url}/feed.json",
        "items": items,
    }
    if site["avatar"]:
        data["icon"] = site["avatar"]
    response = jsonify(data)
    response.content_type = "application/feed+json; charset=utf-8"
    return response
