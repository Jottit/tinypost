import hashlib
import hmac
import secrets
import string

from flask import current_app

from db import count_passcode_attempt, delete_passcode, replace_passcode
from mailer import send_email


def generate_passcode():
    return "".join(secrets.choice(string.digits) for _ in range(6))


def hash_passcode(passcode):
    return hashlib.sha256(passcode.encode()).hexdigest()


def verify_passcode(passcode, hashed):
    return hmac.compare_digest(hashlib.sha256(passcode.encode()).hexdigest(), hashed)


MAX_PASSCODE_ATTEMPTS = 5


def issue_passcode(email, purpose, user_id=None):
    passcode = generate_passcode()
    replace_passcode(user_id, email, purpose, hash_passcode(passcode))
    return passcode


def check_passcode(email, purpose, passcode, user_id=None):
    row = count_passcode_attempt(email, purpose, user_id, MAX_PASSCODE_ATTEMPTS)
    if not row or not verify_passcode(passcode, row["passcode_hash"]):
        return False
    return delete_passcode(row["id"]) is not None


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
