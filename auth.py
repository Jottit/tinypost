import random
import string

from flask import current_app

from mailer import send_email


def generate_passcode():
    return "".join(random.choices(string.digits, k=6))


def send_passcode(email, passcode):
    domain = current_app.config["BASE_DOMAIN"]
    send_email(
        to=email,
        subject="Your Jottit sign-in code",
        text=(
            f"Your sign-in code is: {passcode}\n"
            "\n"
            "This code expires in 10 minutes.\n"
            "\n"
            "If you didn't request this code, you can safely ignore it.\n"
            "\n"
            "\u2014\n"
            "Jottit\n"
            f"https://{domain}"
        ),
    )
