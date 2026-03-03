import json
import logging
import os
import urllib.request

from flask import current_app

logger = logging.getLogger(__name__)


def send_email(to, subject, text, html=None, from_addr=None):
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print(f"[DEV] To: {to} | Subject: {subject}\n{text}")
        return

    if not from_addr:
        from_addr = f"Tinypost <noreply@{current_app.config['BASE_DOMAIN']}>"

    payload = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html

    data = json.dumps(payload).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Tinypost/1.0",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        logger.error("Resend API error %s: %s", e.code, e.read().decode())
        raise
