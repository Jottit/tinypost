import json
from unittest.mock import patch, MagicMock

from mailer import send_email


def test_send_email_with_api_key():
    mock_response = MagicMock()
    with patch.dict("os.environ", {"RESEND_API_KEY": "re_test_123"}), \
         patch("mailer.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        send_email("user@example.com", "Test Subject", "Test body")

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://api.resend.com/emails"
    assert req.get_header("Authorization") == "Bearer re_test_123"
    assert req.get_header("Content-type") == "application/json"

    body = json.loads(req.data)
    assert body["from"] == "Jottit <noreply@jottit.dev>"
    assert body["to"] == ["user@example.com"]
    assert body["subject"] == "Test Subject"
    assert body["text"] == "Test body"


def test_send_email_without_api_key_falls_back_to_print(capsys):
    with patch.dict("os.environ", {}, clear=True):
        send_email("user@example.com", "Subject", "Body")

    output = capsys.readouterr().out
    assert "user@example.com" in output
    assert "Subject" in output
    assert "Body" in output
