import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)


def send_email(to, subject, text):
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print(f"[DEV] To: {to} | Subject: {subject}\n{text}")
        return

    data = json.dumps(
        {
            "from": "Jottit <noreply@jottit.dev>",
            "to": [to],
            "subject": subject,
            "text": text,
        }
    ).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Jottit/1.0",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        logger.error("Resend API error %s: %s", e.code, e.read().decode())
