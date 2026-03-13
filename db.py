import os
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from flask import current_app, g
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/tinypost")

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            check=ConnectionPool.check_connection,
            max_idle=300,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
        )
    return _pool


def get_db():
    if "db" not in g:
        db_name = current_app.config.get("DATABASE")
        if db_name:
            g.db = psycopg.connect(f"dbname={db_name}", row_factory=dict_row)
            g.db_from_pool = False
        else:
            g.db = get_pool().getconn()
            g.db_from_pool = True
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is None:
        return
    if g.pop("db_from_pool", False):
        get_pool().putconn(db)
    else:
        db.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def subdomain_taken(subdomain):
    return query("SELECT id FROM users WHERE subdomain = %s", (subdomain,), one=True)


def create_user(email, subdomain):
    db = get_db()
    user = db.execute(
        "INSERT INTO users (email, subdomain, title) VALUES (%s, %s, %s) RETURNING *",
        (email, subdomain, subdomain),
    ).fetchone()
    db.commit()
    return user


def get_user_by_id(user_id):
    return query("SELECT * FROM users WHERE id = %s", (user_id,), one=True)


def get_user_by_email(email):
    return query("SELECT * FROM users WHERE email = %s", (email,), one=True)


def get_user_by_subdomain(subdomain):
    return query("SELECT * FROM users WHERE subdomain = %s", (subdomain,), one=True)


def get_user_by_custom_domain(domain):
    return query(
        "SELECT * FROM users WHERE custom_domain = %s AND domain_verified_at IS NOT NULL",
        (domain,),
        one=True,
    )


def get_posts_for_user(user_id, include_drafts=False, limit=30, offset=0):
    sql = "SELECT * FROM posts WHERE user_id = %s"
    if not include_drafts:
        sql += " AND is_draft = FALSE"
    sql += " ORDER BY is_pinned DESC, COALESCE(published_at, created_at) DESC LIMIT %s OFFSET %s"
    return query(sql, (user_id, limit, offset))


def get_all_posts_for_user(user_id, limit=1000):
    return query(
        "SELECT * FROM posts WHERE user_id = %s ORDER BY COALESCE(published_at, created_at) DESC"
        " LIMIT %s",
        (user_id, limit),
    )


def get_post_by_slug(user_id, slug):
    return query("SELECT * FROM posts WHERE user_id = %s AND slug = %s", (user_id, slug), one=True)


def create_post(user_id, slug, title, body, is_draft=False):
    db = get_db()
    post = db.execute(
        "INSERT INTO posts (user_id, slug, title, body, is_draft, published_at)"
        " VALUES (%s, %s, %s, %s, %s, CASE WHEN %s THEN NULL ELSE NOW() END) RETURNING *",
        (user_id, slug, title, body, is_draft, is_draft),
    ).fetchone()
    db.commit()
    return post


def update_post(post_id, slug, title, body, is_draft=False):
    db = get_db()
    post = db.execute(
        "UPDATE posts SET slug = %s, title = %s, body = %s, is_draft = %s, updated_at = NOW(),"
        " published_at = CASE WHEN published_at IS NULL AND NOT %s THEN NOW() ELSE published_at END"
        " WHERE id = %s RETURNING *",
        (slug, title, body, is_draft, is_draft, post_id),
    ).fetchone()
    db.commit()
    return post


def update_user_blog(user_id, title, bio, license=None):
    db = get_db()
    user = db.execute(
        "UPDATE users SET title = %s, bio = %s, license = %s,"
        " updated_at = NOW() WHERE id = %s RETURNING *",
        (title, bio, license, user_id),
    ).fetchone()
    db.commit()
    return user


def update_user_links(user_id, links):
    db = get_db()
    user = db.execute(
        "UPDATE users SET links = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (Json(links or []), user_id),
    ).fetchone()
    db.commit()
    return user


def update_user_license(user_id, license):
    db = get_db()
    user = db.execute(
        "UPDATE users SET license = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (license, user_id),
    ).fetchone()
    db.commit()
    return user


def update_user_subdomain(user_id, subdomain):
    db = get_db()
    user = db.execute(
        "UPDATE users SET subdomain = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (subdomain, user_id),
    ).fetchone()
    db.commit()
    return user


def update_user_avatar(user_id, avatar_url):
    db = get_db()
    user = db.execute(
        "UPDATE users SET avatar = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (avatar_url, user_id),
    ).fetchone()
    db.commit()
    return user


def update_user_theme(user_id, theme):
    db = get_db()
    user = db.execute(
        "UPDATE users SET theme = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (theme, user_id),
    ).fetchone()
    db.commit()
    return user


def delete_post(post_id):
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    db.commit()


def set_custom_domain(user_id, domain, token):
    db = get_db()
    user = db.execute(
        "UPDATE users SET custom_domain = %s, domain_verification_token = %s,"
        " domain_verified_at = NULL, updated_at = NOW() WHERE id = %s RETURNING *",
        (domain, token, user_id),
    ).fetchone()
    db.commit()
    return user


def verify_custom_domain(user_id):
    db = get_db()
    user = db.execute(
        "UPDATE users SET domain_verified_at = NOW(), updated_at = NOW()"
        " WHERE id = %s RETURNING *",
        (user_id,),
    ).fetchone()
    db.commit()
    return user


def remove_custom_domain(user_id):
    db = get_db()
    user = db.execute(
        "UPDATE users SET custom_domain = NULL, domain_verified_at = NULL,"
        " domain_verification_token = NULL, updated_at = NOW() WHERE id = %s RETURNING *",
        (user_id,),
    ).fetchone()
    db.commit()
    return user


def is_domain_taken(domain, exclude_user_id=None):
    if exclude_user_id is not None:
        return query(
            "SELECT id FROM users WHERE custom_domain = %s AND id != %s",
            (domain, exclude_user_id),
            one=True,
        )
    return query("SELECT id FROM users WHERE custom_domain = %s", (domain,), one=True)


def update_user_email(user_id, email):
    db = get_db()
    user = db.execute(
        "UPDATE users SET email = %s WHERE id = %s RETURNING *",
        (email, user_id),
    ).fetchone()
    db.commit()
    return user


def update_user(user_id, name, email):
    db = get_db()
    user = db.execute(
        "UPDATE users SET name = %s, email = %s WHERE id = %s RETURNING *",
        (name, email, user_id),
    ).fetchone()
    db.commit()
    return user


def delete_account(user_id):
    db = get_db()
    db.execute("DELETE FROM indieauth_codes WHERE user_id = %s", (user_id,))
    db.execute("DELETE FROM blogroll WHERE user_id = %s", (user_id,))
    db.execute("DELETE FROM subscribers WHERE user_id = %s", (user_id,))
    db.execute("DELETE FROM posts WHERE user_id = %s", (user_id,))
    db.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db.commit()


def get_subscriber(user_id, email):
    return query(
        "SELECT * FROM subscribers WHERE user_id = %s AND email = %s",
        (user_id, email),
        one=True,
    )


def create_subscriber(user_id, email, token):
    db = get_db()
    subscriber = db.execute(
        "INSERT INTO subscribers (user_id, email, token) VALUES (%s, %s, %s) RETURNING *",
        (user_id, email, token),
    ).fetchone()
    db.commit()
    return subscriber


def update_subscriber_token(subscriber_id, token):
    db = get_db()
    subscriber = db.execute(
        "UPDATE subscribers SET token = %s, confirmed = FALSE WHERE id = %s RETURNING *",
        (token, subscriber_id),
    ).fetchone()
    db.commit()
    return subscriber


def get_subscriber_by_token(token):
    return query("SELECT * FROM subscribers WHERE token = %s", (token,), one=True)


def confirm_subscriber(token):
    db = get_db()
    subscriber = db.execute(
        "UPDATE subscribers SET confirmed = TRUE WHERE token = %s RETURNING *",
        (token,),
    ).fetchone()
    db.commit()
    return subscriber


def unsubscribe(token):
    db = get_db()
    db.execute("DELETE FROM subscribers WHERE token = %s", (token,))
    db.commit()


def delete_subscriber(subscriber_id, user_id):
    db = get_db()
    db.execute(
        "DELETE FROM subscribers WHERE id = %s AND user_id = %s",
        (subscriber_id, user_id),
    )
    db.commit()


def get_all_subscribers(user_id):
    return query(
        "SELECT * FROM subscribers WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )


def get_confirmed_subscribers(user_id):
    return query(
        "SELECT * FROM subscribers WHERE user_id = %s AND confirmed = TRUE",
        (user_id,),
    )


def get_subscriber_count(user_id):
    row = query(
        "SELECT COUNT(*) AS count FROM subscribers WHERE user_id = %s AND confirmed = TRUE",
        (user_id,),
        one=True,
    )
    return row["count"]


def has_blogroll(user_id):
    row = query(
        "SELECT EXISTS(SELECT 1 FROM blogroll WHERE user_id = %s) AS has",
        (user_id,),
        one=True,
    )
    return row["has"]


def get_blogroll(user_id):
    return query(
        "SELECT b.id, b.user_id, b.name, b.sort_order, b.created_at,"
        " f.url, f.feed_url, f.feed_title, f.feed_icon_url,"
        " f.latest_post_title, f.latest_post_url, f.last_updated, f.last_fetched"
        " FROM blogroll b JOIN feeds f ON b.feed_id = f.id"
        " WHERE b.user_id = %s"
        " ORDER BY f.last_updated DESC NULLS LAST, b.sort_order",
        (user_id,),
    )


def update_blogroll(user_id, items):
    db = get_db()
    existing = {
        row["url"]: row
        for row in query(
            "SELECT b.id, f.url FROM blogroll b JOIN feeds f ON b.feed_id = f.id"
            " WHERE b.user_id = %s",
            (user_id,),
        )
    }
    new_urls = {item["url"] for item in items}

    for url in existing.keys() - new_urls:
        db.execute("DELETE FROM blogroll WHERE id = %s", (existing[url]["id"],))

    for i, item in enumerate(items):
        feed_id = _find_or_create_feed(db, item["url"], item.get("feed_url"))
        if item["url"] in existing:
            db.execute(
                "UPDATE blogroll SET name = %s, sort_order = %s, feed_id = %s WHERE id = %s",
                (item["name"], i, feed_id, existing[item["url"]]["id"]),
            )
        else:
            db.execute(
                "INSERT INTO blogroll (user_id, name, feed_id, sort_order)"
                " VALUES (%s, %s, %s, %s)",
                (user_id, item["name"], feed_id, i),
            )
    db.commit()


def _find_or_create_feed(db, url, feed_url=None):
    row = db.execute(
        "INSERT INTO feeds (url, feed_url) VALUES (%s, %s)"
        " ON CONFLICT (url) DO UPDATE SET url = EXCLUDED.url"
        " RETURNING id",
        (url, feed_url),
    ).fetchone()
    return row["id"]


def mark_post_sent(post_id):
    db = get_db()
    post = db.execute(
        "UPDATE posts SET sent_at = NOW() WHERE id = %s RETURNING *",
        (post_id,),
    ).fetchone()
    db.commit()
    return post


def toggle_post_pinned(post_id):
    db = get_db()
    post = db.execute(
        "UPDATE posts SET is_pinned = NOT is_pinned WHERE id = %s RETURNING *",
        (post_id,),
    ).fetchone()
    db.commit()
    return post


def create_auth_code(
    user_id,
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
        "INSERT INTO indieauth_codes (user_id, code, client_id, redirect_uri, scope,"
        " code_challenge, code_challenge_method, expires_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            user_id,
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


def get_personal_token(user_id):
    return query(
        "SELECT * FROM indieauth_codes WHERE user_id = %s AND client_id = 'personal-token'",
        (user_id,),
        one=True,
    )


def create_personal_token(user_id):
    revoke_personal_token(user_id)
    db = get_db()
    token = secrets.token_urlsafe(32)
    code = secrets.token_urlsafe(16)
    expires_at = datetime.now(timezone.utc) + timedelta(days=365 * 10)
    db.execute(
        "INSERT INTO indieauth_codes (user_id, code, client_id, redirect_uri, scope,"
        " code_challenge, code_challenge_method, token, used_at, expires_at)"
        " VALUES (%s, %s, 'personal-token', '', 'create', '', 'S256', %s, NOW(), %s)",
        (user_id, code, token, expires_at),
    )
    db.commit()
    return token


def revoke_personal_token(user_id):
    db = get_db()
    db.execute(
        "DELETE FROM indieauth_codes WHERE user_id = %s AND client_id = 'personal-token'",
        (user_id,),
    )
    db.commit()
