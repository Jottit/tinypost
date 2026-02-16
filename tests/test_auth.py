from unittest.mock import patch

from app import app
from auth import send_passcode


@patch("auth.send_email")
def test_send_passcode(mock_send_email):
    with app.app_context():
        send_passcode("user@example.com", "123456")

    mock_send_email.assert_called_once_with(
        to="user@example.com",
        subject="Your Jottit sign-in code",
        text=(
            "Your sign-in code is: 123456\n"
            "\n"
            "This code expires in 10 minutes.\n"
            "\n"
            "If you didn't request this code, you can safely ignore it.\n"
            "\n"
            "\u2014\n"
            "Jottit\n"
            f"https://{app.config['BASE_DOMAIN']}"
        ),
    )
