import hashlib
import hmac
import secrets
import string

from flask import current_app

from mailer import send_email


def generate_passcode():
    return "".join(secrets.choice(string.digits) for _ in range(6))


def hash_passcode(passcode):
    return hashlib.sha256(passcode.encode()).hexdigest()


def verify_passcode(passcode, hashed):
    return hmac.compare_digest(hashlib.sha256(passcode.encode()).hexdigest(), hashed)


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
