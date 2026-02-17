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


def get_posts_for_site(site_id):
    return query(
        "SELECT * FROM posts WHERE site_id = %s ORDER BY created_at DESC LIMIT 30", (site_id,)
    )


def get_user_by_email(email):
    return query("SELECT * FROM users WHERE email = %s", (email,), one=True)


def get_site_by_user(user_id):
    return query("SELECT * FROM sites WHERE user_id = %s", (user_id,), one=True)


def get_post_by_slug(site_id, slug):
    return query("SELECT * FROM posts WHERE site_id = %s AND slug = %s", (site_id, slug), one=True)


def create_post(site_id, slug, title, body):
    db = get_db()
    post = db.execute(
        "INSERT INTO posts (site_id, slug, title, body) VALUES (%s, %s, %s, %s) RETURNING *",
        (site_id, slug, title, body),
    ).fetchone()
    db.commit()
    return post


def update_post(post_id, slug, title, body):
    db = get_db()
    post = db.execute(
        "UPDATE posts SET slug = %s, title = %s, body = %s, updated_at = NOW()"
        " WHERE id = %s RETURNING *",
        (slug, title, body, post_id),
    ).fetchone()
    db.commit()
    return post


def update_site(site_id, title, bio):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET title = %s, bio = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (title, bio, site_id),
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


def delete_post(post_id):
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    db.commit()
