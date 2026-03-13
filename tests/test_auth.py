from unittest.mock import patch

from app import app
from auth import send_passcode
from db import create_user


@patch("auth.send_email")
def test_send_passcode(mock_send_email):
    with app.app_context():
        send_passcode("user@example.com", "123456")

    mock_send_email.assert_called_once_with(
        to="user@example.com",
        subject="Your Tinypost sign-in code",
        text=(
            "Your sign-in code is: 123456\n"
            "\n"
            "This code expires in 10 minutes.\n"
            "\n"
            "If you didn't request this code, you can safely ignore it.\n"
            "\n"
            "\u2014\n"
            "Tinypost\n"
            f"https://{app.config['BASE_DOMAIN']}"
        ),
    )


def test_signup_rejects_existing_email(client):
    with app.app_context():
        create_user("taken@example.com", "taken")
    resp = client.post(
        "/signup",
        data={"subdomain": "newblog", "email": "taken@example.com"},
        headers={"Host": "tinypost.localhost:8000"},
    )
    assert resp.status_code == 200
    assert b"already registered" in resp.data
