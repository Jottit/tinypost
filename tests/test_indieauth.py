import base64
import hashlib
import re
from unittest.mock import patch

from app import app
from db import create_user


def extract_hidden(html, name):
    match = re.search(rf'name="{name}"\s+value="([^"]*)"', html)
    return match.group(1) if match else ""


def make_site(client):
    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    return user


def pkce_pair():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


AUTH_PARAMS = {
    "response_type": "code",
    "client_id": "https://example.com",
    "redirect_uri": "https://example.com/callback",
    "code_challenge_method": "S256",
    "state": "teststate",
}


def auth_params(challenge):
    return {**AUTH_PARAMS, "code_challenge": challenge}


class TestMetadata:
    def test_metadata_returns_json(self, client):
        make_site(client)
        resp = client.get(
            "/.well-known/oauth-authorization-server",
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert data["code_challenge_methods_supported"] == ["S256"]

    def test_metadata_404_no_site(self, client):
        resp = client.get(
            "/.well-known/oauth-authorization-server",
            base_url="http://nonexistent.tinypost.localhost:8000",
        )
        assert resp.status_code == 404


class TestAuthorizeGet:
    def test_missing_response_type(self, client):
        make_site(client)
        resp = client.get(
            "/auth?client_id=https://example.com&redirect_uri=https://example.com/cb&code_challenge=test",
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 400

    def test_missing_code_challenge_allowed(self, client):
        make_site(client)
        resp = client.get(
            "/auth?response_type=code&client_id=https://example.com&redirect_uri=https://example.com/cb",
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200

    def test_shows_send_passcode_when_not_authenticated(self, client):
        make_site(client)
        _, challenge = pkce_pair()
        resp = client.get(
            "/auth",
            query_string=auth_params(challenge),
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        assert b"Send code to" in resp.data

    def test_shows_approve_when_authenticated(self, client):
        user = make_site(client)
        with client.session_transaction() as sess:
            sess["user_id"] = user["id"]
        _, challenge = pkce_pair()
        resp = client.get(
            "/auth",
            query_string=auth_params(challenge),
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        assert b"Approve" in resp.data


class TestPasscodeFlow:
    @patch("routes.indieauth.send_passcode")
    def test_send_passcode(self, mock_send, client):
        make_site(client)
        _, challenge = pkce_pair()
        resp = client.post(
            "/auth",
            data={**auth_params(challenge), "action": "send_passcode"},
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        assert b"6-digit code" in resp.data
        assert b"passcode_token" in resp.data
        mock_send.assert_called_once()

    @patch("routes.indieauth.send_passcode")
    def test_verify_correct_passcode(self, mock_send, client):
        make_site(client)
        _, challenge = pkce_pair()
        resp = client.post(
            "/auth",
            data={**auth_params(challenge), "action": "send_passcode"},
            base_url="http://myblog.tinypost.localhost:8000",
        )
        html = resp.data.decode()
        passcode_token = extract_hidden(html, "passcode_token")
        passcode = mock_send.call_args[0][1]
        resp = client.post(
            "/auth",
            data={
                **auth_params(challenge),
                "action": "verify_passcode",
                "passcode": passcode,
                "passcode_token": passcode_token,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        assert b"Approve" in resp.data
        assert b"auth_token" in resp.data

    @patch("routes.indieauth.send_passcode")
    def test_verify_wrong_passcode(self, mock_send, client):
        make_site(client)
        _, challenge = pkce_pair()
        resp = client.post(
            "/auth",
            data={**auth_params(challenge), "action": "send_passcode"},
            base_url="http://myblog.tinypost.localhost:8000",
        )
        html = resp.data.decode()
        passcode_token = extract_hidden(html, "passcode_token")
        resp = client.post(
            "/auth",
            data={
                **auth_params(challenge),
                "action": "verify_passcode",
                "passcode": "000000",
                "passcode_token": passcode_token,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        assert b"Wrong passcode" in resp.data


class TestApproveAndDeny:
    def _get_auth_token(self, client, user, challenge):
        with client.session_transaction() as sess:
            sess["user_id"] = user["id"]
        resp = client.get(
            "/auth",
            query_string=auth_params(challenge),
            base_url="http://myblog.tinypost.localhost:8000",
        )
        return extract_hidden(resp.data.decode(), "auth_token")

    def test_approve_redirects_with_code(self, client):
        user = make_site(client)
        _, challenge = pkce_pair()
        auth_token = self._get_auth_token(client, user, challenge)
        resp = client.post(
            "/auth",
            data={**auth_params(challenge), "action": "approve", "auth_token": auth_token},
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "https://example.com/callback?" in location
        assert "code=" in location
        assert "state=teststate" in location
        assert "iss=" in location

    def test_deny_redirects_with_error(self, client):
        user = make_site(client)
        _, challenge = pkce_pair()
        resp = client.post(
            "/auth",
            data={**auth_params(challenge), "action": "deny"},
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "error=access_denied" in location

    def test_approve_unauthenticated_shows_send_passcode(self, client):
        make_site(client)
        _, challenge = pkce_pair()
        resp = client.post(
            "/auth",
            data={**auth_params(challenge), "action": "approve"},
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        assert b"Not authenticated" in resp.data


class TestTokenExchange:
    def _get_auth_token(self, client, user, challenge):
        with client.session_transaction() as sess:
            sess["user_id"] = user["id"]
        resp = client.get(
            "/auth",
            query_string=auth_params(challenge),
            base_url="http://myblog.tinypost.localhost:8000",
        )
        return extract_hidden(resp.data.decode(), "auth_token")

    def _get_code(self, client, user, challenge):
        auth_token = self._get_auth_token(client, user, challenge)
        resp = client.post(
            "/auth",
            data={
                **auth_params(challenge),
                "action": "approve",
                "scope": "create",
                "auth_token": auth_token,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(resp.headers["Location"]).query)
        return qs["code"][0]

    def test_valid_exchange(self, client):
        user = make_site(client)
        verifier, challenge = pkce_pair()
        code = self._get_code(client, user, challenge)
        resp = client.post(
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "https://example.com",
                "redirect_uri": "https://example.com/callback",
                "code_verifier": verifier,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["scope"] == "create"
        assert "me" in data

    def test_wrong_verifier(self, client):
        user = make_site(client)
        _, challenge = pkce_pair()
        code = self._get_code(client, user, challenge)
        resp = client.post(
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "https://example.com",
                "redirect_uri": "https://example.com/callback",
                "code_verifier": "wrong-verifier",
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 400

    def test_wrong_client_id(self, client):
        user = make_site(client)
        verifier, challenge = pkce_pair()
        code = self._get_code(client, user, challenge)
        resp = client.post(
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "https://evil.com",
                "redirect_uri": "https://example.com/callback",
                "code_verifier": verifier,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 400

    def test_wrong_redirect_uri(self, client):
        user = make_site(client)
        verifier, challenge = pkce_pair()
        code = self._get_code(client, user, challenge)
        resp = client.post(
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "https://example.com",
                "redirect_uri": "https://evil.com/callback",
                "code_verifier": verifier,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 400

    def test_code_single_use(self, client):
        user = make_site(client)
        verifier, challenge = pkce_pair()
        code = self._get_code(client, user, challenge)
        # First exchange succeeds
        resp = client.post(
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "https://example.com",
                "redirect_uri": "https://example.com/callback",
                "code_verifier": verifier,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        # Second exchange fails
        resp = client.post(
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "https://example.com",
                "redirect_uri": "https://example.com/callback",
                "code_verifier": verifier,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 400

    def test_identity_only_no_access_token(self, client):
        user = make_site(client)
        verifier, challenge = pkce_pair()
        auth_token = self._get_auth_token(client, user, challenge)
        resp = client.post(
            "/auth",
            data={
                **auth_params(challenge),
                "action": "approve",
                "scope": "",
                "auth_token": auth_token,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(resp.headers["Location"]).query)
        code = qs["code"][0]
        resp = client.post(
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "https://example.com",
                "redirect_uri": "https://example.com/callback",
                "code_verifier": verifier,
            },
            base_url="http://myblog.tinypost.localhost:8000",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "me" in data
        assert "access_token" not in data


class TestLinkTags:
    def test_homepage_has_indieauth_links(self, client):
        make_site(client)
        resp = client.get("/", base_url="http://myblog.tinypost.localhost:8000")
        html = resp.data.decode()
        assert 'rel="indieauth-metadata"' in html
        base = "http://myblog.tinypost.localhost:8000"
        assert f'href="{base}/.well-known/oauth-authorization-server"' in html
        assert 'rel="authorization_endpoint"' in html
        assert 'href="http://myblog.tinypost.localhost:8000/auth"' in html
        assert 'rel="token_endpoint"' in html
        assert 'href="http://myblog.tinypost.localhost:8000/auth/token"' in html

    def test_post_page_has_indieauth_links(self, client):
        user = make_site(client)
        from db import create_post

        with app.app_context():
            create_post(user["id"], "hello", "Hello", "World")
        resp = client.get("/hello", base_url="http://myblog.tinypost.localhost:8000")
        html = resp.data.decode()
        assert 'rel="indieauth-metadata"' in html
        assert 'href="http://myblog.tinypost.localhost:8000/auth"' in html
