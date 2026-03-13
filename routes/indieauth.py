import base64
import hashlib
import secrets
from urllib.parse import urlencode, urlparse

from flask import abort, jsonify, redirect, render_template, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app import app, limiter
from auth import generate_passcode, send_passcode
from db import create_auth_code, exchange_auth_code, get_auth_code, get_user_by_id
from utils import get_current_site, mask_email, site_url

_serializer = URLSafeTimedSerializer(app.secret_key, salt="indieauth-passcode")


def _indieauth_params():
    src = request.form if request.method == "POST" else request.args
    return {
        "response_type": src.get("response_type", ""),
        "client_id": src.get("client_id", ""),
        "redirect_uri": src.get("redirect_uri", ""),
        "state": src.get("state", ""),
        "scope": src.get("scope", ""),
        "code_challenge": src.get("code_challenge", ""),
        "code_challenge_method": src.get("code_challenge_method", "S256"),
    }


def _validate_params(params):
    if params["response_type"] != "code":
        return "Missing or invalid response_type"
    if not params["client_id"]:
        return "Missing client_id"
    if not params["redirect_uri"]:
        return "Missing redirect_uri"
    c = urlparse(params["client_id"])
    r = urlparse(params["redirect_uri"])
    if (c.scheme, c.netloc) != (r.scheme, r.netloc):
        return "redirect_uri must be on the same domain as client_id"
    return None


def _consent_template(site, step, params, **kwargs):
    me = site_url(site)
    return render_template(
        "indieauth_consent.html",
        site=site,
        me=me,
        step=step,
        masked_email=mask_email(site["email"]),
        **params,
        **kwargs,
    )


@app.route("/.well-known/oauth-authorization-server")
def indieauth_metadata():
    site = get_current_site()
    if not site:
        abort(404)
    base = site_url(site)
    return jsonify(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/auth",
            "token_endpoint": f"{base}/auth/token",
            "code_challenge_methods_supported": ["S256"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
        }
    )


@app.route("/auth", methods=["GET"])
def indieauth_authorize():
    site = get_current_site()
    if not site:
        abort(404)

    params = _indieauth_params()
    error = _validate_params(params)
    if error:
        abort(400, error)

    is_owner = session.get("user_id") == site["id"]
    if is_owner:
        auth_token = _serializer.dumps({"user_id": site["id"], "authenticated": True})
        return _consent_template(site, "approve", params, auth_token=auth_token)
    return _consent_template(site, "send_passcode", params)


@app.route("/auth", methods=["POST"])
@limiter.limit("10/minute")
def indieauth_authorize_post():
    site = get_current_site()
    if not site:
        abort(404)

    params = _indieauth_params()
    error = _validate_params(params)
    if error:
        abort(400, error)

    action = request.form.get("action", "")

    if action == "send_passcode":
        passcode = generate_passcode()
        token = _serializer.dumps({"passcode": passcode, "user_id": site["id"]})
        send_passcode(site["email"], passcode)
        return _consent_template(site, "verify_passcode", params, passcode_token=token)

    if action == "verify_passcode":
        passcode = request.form.get("passcode", "")
        token = request.form.get("passcode_token", "")
        try:
            data = _serializer.loads(token, max_age=600)
        except (BadSignature, SignatureExpired):
            return _consent_template(
                site,
                "send_passcode",
                params,
                error="Code expired. Try again.",
            )
        if data["user_id"] != site["id"] or data["passcode"] != passcode:
            return _consent_template(
                site,
                "verify_passcode",
                params,
                passcode_token=token,
                error="Wrong passcode.",
            )
        auth_token = _serializer.dumps({"user_id": site["id"], "authenticated": True})
        session["user_id"] = site["id"]
        return _consent_template(site, "approve", params, auth_token=auth_token)

    if action == "deny":
        qs = urlencode({"error": "access_denied", "state": params["state"]})
        return redirect(f"{params['redirect_uri']}?{qs}")

    if action == "approve":
        is_owner = session.get("user_id") == site["id"]
        if not is_owner:
            token = request.form.get("auth_token", "")
            try:
                data = _serializer.loads(token, max_age=600)
                is_owner = data.get("user_id") == site["id"] and data.get("authenticated")
            except (BadSignature, SignatureExpired):
                pass
        if not is_owner:
            return _consent_template(site, "send_passcode", params, error="Not authenticated.")

        code = secrets.token_urlsafe(32)
        create_auth_code(
            site["id"],
            code,
            params["client_id"],
            params["redirect_uri"],
            params["scope"],
            params["code_challenge"],
            params["code_challenge_method"],
        )
        me = site_url(site)
        qs = urlencode({"code": code, "state": params["state"], "iss": me})
        return redirect(f"{params['redirect_uri']}?{qs}")

    abort(400, "Unknown action")


@app.route("/auth/token", methods=["POST"])
def indieauth_token():
    grant_type = request.form.get("grant_type", "")
    if grant_type != "authorization_code":
        return jsonify({"error": "unsupported_grant_type"}), 400

    code = request.form.get("code", "")
    client_id = request.form.get("client_id", "")
    redirect_uri = request.form.get("redirect_uri", "")
    code_verifier = request.form.get("code_verifier", "")

    auth_code = get_auth_code(code)
    if not auth_code:
        return jsonify({"error": "invalid_grant"}), 400

    if auth_code["client_id"] != client_id:
        return jsonify({"error": "invalid_grant"}), 400
    if auth_code["redirect_uri"] != redirect_uri:
        return jsonify({"error": "invalid_grant"}), 400

    # Verify PKCE (if the client used it)
    if auth_code["code_challenge"]:
        digest = hashlib.sha256(code_verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if expected != auth_code["code_challenge"]:
            return jsonify({"error": "invalid_grant"}), 400

    site = get_user_by_id(auth_code["user_id"])
    me = site_url(site)

    scope = auth_code["scope"]
    if not scope:
        exchange_auth_code(code, "used")
        return jsonify({"me": me})

    token = secrets.token_urlsafe(32)
    exchange_auth_code(code, token)
    return jsonify(
        {
            "access_token": token,
            "token_type": "Bearer",
            "scope": scope,
            "me": me,
        }
    )
