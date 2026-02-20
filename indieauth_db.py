from datetime import datetime, timedelta, timezone

from models import get_db, query


def create_auth_code(site_id, code, client_id, redirect_uri, scope, code_challenge, code_challenge_method):
    db = get_db()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.execute(
        "INSERT INTO indieauth_codes (site_id, code, client_id, redirect_uri, scope,"
        " code_challenge, code_challenge_method, expires_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (site_id, code, client_id, redirect_uri, scope, code_challenge, code_challenge_method, expires_at),
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
