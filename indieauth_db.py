import secrets
from datetime import datetime, timedelta, timezone

from db import get_db, query


def create_auth_code(
    site_id,
    code,
    client_id,
    redirect_uri,
    scope,
    code_challenge,
    code_challenge_method,
):
    db = get_db()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.execute(
        "INSERT INTO indieauth_codes (site_id, code, client_id, redirect_uri, scope,"
        " code_challenge, code_challenge_method, expires_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            site_id,
            code,
            client_id,
            redirect_uri,
            scope,
            code_challenge,
            code_challenge_method,
            expires_at,
        ),
    )
    db.commit()


def get_auth_code(code):
    return query(
        "SELECT * FROM indieauth_codes WHERE code = %s AND used_at IS NULL AND expires_at > NOW()",
        (code,),
        one=True,
    )


def exchange_auth_code(code, token):
    db = get_db()
    row = db.execute(
        "UPDATE indieauth_codes SET token = %s, used_at = NOW()"
        " WHERE code = %s AND used_at IS NULL AND expires_at > NOW() RETURNING *",
        (token, code),
    ).fetchone()
    db.commit()
    return row


def get_token(token):
    return query(
        "SELECT * FROM indieauth_codes WHERE token = %s",
        (token,),
        one=True,
    )


def get_personal_token(site_id):
    return query(
        "SELECT * FROM indieauth_codes WHERE site_id = %s AND client_id = 'personal-token'",
        (site_id,),
        one=True,
    )


def create_personal_token(site_id):
    revoke_personal_token(site_id)
    db = get_db()
    token = secrets.token_urlsafe(32)
    code = secrets.token_urlsafe(16)
    expires_at = datetime.now(timezone.utc) + timedelta(days=365 * 10)
    db.execute(
        "INSERT INTO indieauth_codes (site_id, code, client_id, redirect_uri, scope,"
        " code_challenge, code_challenge_method, token, used_at, expires_at)"
        " VALUES (%s, %s, 'personal-token', '', 'create', '', 'S256', %s, NOW(), %s)",
        (site_id, code, token, expires_at),
    )
    db.commit()
    return token


def revoke_personal_token(site_id):
    db = get_db()
    db.execute(
        "DELETE FROM indieauth_codes WHERE site_id = %s AND client_id = 'personal-token'",
        (site_id,),
    )
    db.commit()
