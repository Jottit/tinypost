from psycopg.types.json import Json

from models import get_db, query


def subdomain_taken(subdomain):
    return query("SELECT id FROM sites WHERE subdomain = %s", (subdomain,), one=True)


def create_user_and_site(email, subdomain):
    db = get_db()
    user = db.execute(
        "INSERT INTO users (email) VALUES (%s) ON CONFLICT (email) DO NOTHING RETURNING id",
        (email,),
    ).fetchone()
    if not user:
        user = db.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()
    site = db.execute(
        "INSERT INTO sites (subdomain, user_id, title) VALUES (%s, %s, %s) RETURNING *",
        (subdomain, user["id"], subdomain),
    ).fetchone()
    db.commit()
    return user, site


def get_site_by_subdomain(subdomain):
    return query("SELECT * FROM sites WHERE subdomain = %s", (subdomain,), one=True)


def get_posts_for_site(site_id, include_drafts=False):
    sql = "SELECT * FROM posts WHERE site_id = %s"
    if not include_drafts:
        sql += " AND is_draft = FALSE"
    sql += " ORDER BY created_at DESC LIMIT 30"
    return query(sql, (site_id,))


def get_all_posts_for_site(site_id):
    return query("SELECT * FROM posts WHERE site_id = %s ORDER BY created_at DESC", (site_id,))


def get_user_by_id(user_id):
    return query("SELECT * FROM users WHERE id = %s", (user_id,), one=True)


def get_user_by_email(email):
    return query("SELECT * FROM users WHERE email = %s", (email,), one=True)


def get_site_by_user(user_id):
    return query("SELECT * FROM sites WHERE user_id = %s", (user_id,), one=True)


def get_post_by_slug(site_id, slug):
    return query("SELECT * FROM posts WHERE site_id = %s AND slug = %s", (site_id, slug), one=True)


def create_post(site_id, slug, title, body, is_draft=False):
    db = get_db()
    post = db.execute(
        "INSERT INTO posts (site_id, slug, title, body, is_draft)"
        " VALUES (%s, %s, %s, %s, %s) RETURNING *",
        (site_id, slug, title, body, is_draft),
    ).fetchone()
    db.commit()
    return post


def update_post(post_id, slug, title, body, is_draft=False):
    db = get_db()
    post = db.execute(
        "UPDATE posts SET slug = %s, title = %s, body = %s, is_draft = %s, updated_at = NOW()"
        " WHERE id = %s RETURNING *",
        (slug, title, body, is_draft, post_id),
    ).fetchone()
    db.commit()
    return post


def update_site(site_id, title, bio, license=None):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET title = %s, bio = %s, license = %s, updated_at = NOW()"
        " WHERE id = %s RETURNING *",
        (title, bio, license, site_id),
    ).fetchone()
    db.commit()
    return site


def update_site_avatar(site_id, avatar_url):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET avatar = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (avatar_url, site_id),
    ).fetchone()
    db.commit()
    return site


def update_site_design(site_id, design):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET design = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (Json(design), site_id),
    ).fetchone()
    db.commit()
    return site


def delete_post(post_id):
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    db.commit()


def get_site_by_custom_domain(domain):
    return query(
        "SELECT * FROM sites WHERE custom_domain = %s AND domain_verified_at IS NOT NULL",
        (domain,),
        one=True,
    )


def set_custom_domain(site_id, domain, token):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET custom_domain = %s, domain_verification_token = %s,"
        " domain_verified_at = NULL, updated_at = NOW() WHERE id = %s RETURNING *",
        (domain, token, site_id),
    ).fetchone()
    db.commit()
    return site


def verify_custom_domain(site_id):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET domain_verified_at = NOW(), updated_at = NOW()"
        " WHERE id = %s RETURNING *",
        (site_id,),
    ).fetchone()
    db.commit()
    return site


def remove_custom_domain(site_id):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET custom_domain = NULL, domain_verified_at = NULL,"
        " domain_verification_token = NULL, updated_at = NOW() WHERE id = %s RETURNING *",
        (site_id,),
    ).fetchone()
    db.commit()
    return site


def is_domain_taken(domain, exclude_site_id=None):
    if exclude_site_id is not None:
        return query(
            "SELECT id FROM sites WHERE custom_domain = %s AND id != %s",
            (domain, exclude_site_id),
            one=True,
        )
    return query("SELECT id FROM sites WHERE custom_domain = %s", (domain,), one=True)


def delete_account(user_id):
    db = get_db()
    site = get_site_by_user(user_id)
    if site:
        db.execute("DELETE FROM posts WHERE site_id = %s", (site["id"],))
        db.execute("DELETE FROM sites WHERE id = %s", (site["id"],))
    db.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db.commit()
