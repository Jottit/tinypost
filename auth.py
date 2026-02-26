import secrets
import string

from flask import current_app

from mailer import send_email


def generate_passcode():
    return "".join(secrets.choice(string.digits) for _ in range(6))


def send_passcode(email, passcode):
    domain = current_app.config["BASE_DOMAIN"]
    send_email(
        to=email,
        subject="Your Tinypost sign-in code",
        text=(
            f"Your sign-in code is: {passcode}\n"
            "\n"
            "This code expires in 10 minutes.\n"
            "\n"
            "If you didn't request this code, you can safely ignore it.\n"
            "\n"
            "\u2014\n"
            "Tinypost\n"
            f"https://{domain}"
        ),
    )
