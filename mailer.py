import json
import os
import urllib.request


def send_email(to, subject, text):
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print(f"[DEV] To: {to} | Subject: {subject}\n{text}")
        return

    data = json.dumps({
        "from": "Jottit <noreply@jottit.dev>",
        "to": [to],
        "subject": subject,
        "text": text,
    }).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    urllib.request.urlopen(req)
