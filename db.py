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


def get_site_by_id(site_id):
    return query("SELECT * FROM sites WHERE id = %s", (site_id,), one=True)


def get_site_by_subdomain(subdomain):
    return query("SELECT * FROM sites WHERE subdomain = %s", (subdomain,), one=True)


def get_posts_for_site(site_id, include_drafts=False):
    sql = "SELECT * FROM posts WHERE site_id = %s"
    if not include_drafts:
        sql += " AND is_draft = FALSE"
    sql += " ORDER BY COALESCE(published_at, created_at) DESC LIMIT 30"
    return query(sql, (site_id,))


def get_all_posts_for_site(site_id):
    return query(
        "SELECT * FROM posts WHERE site_id = %s ORDER BY COALESCE(published_at, created_at) DESC",
        (site_id,),
    )


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
        "INSERT INTO posts (site_id, slug, title, body, is_draft, published_at)"
        " VALUES (%s, %s, %s, %s, %s, CASE WHEN %s THEN NULL ELSE NOW() END) RETURNING *",
        (site_id, slug, title, body, is_draft, is_draft),
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


def update_site(site_id, title, bio, license=None, social_links=None):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET title = %s, bio = %s, license = %s, social_links = %s, updated_at = NOW()"
        " WHERE id = %s RETURNING *",
        (title, bio, license, Json(social_links or []), site_id),
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


def update_site_custom_css(site_id, custom_css):
    db = get_db()
    site = db.execute(
        "UPDATE sites SET custom_css = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (custom_css, site_id),
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


def update_user_email(user_id, email):
    db = get_db()
    user = db.execute(
        "UPDATE users SET email = %s WHERE id = %s RETURNING *",
        (email, user_id),
    ).fetchone()
    db.commit()
    return user


def get_pages_for_site(site_id, include_drafts=False):
    sql = "SELECT * FROM pages WHERE site_id = %s"
    if not include_drafts:
        sql += " AND is_draft = FALSE"
    sql += " ORDER BY sort_order"
    return query(sql, (site_id,))


def get_page_by_slug(site_id, slug):
    return query("SELECT * FROM pages WHERE site_id = %s AND slug = %s", (site_id, slug), one=True)


def get_page_by_id(page_id):
    return query("SELECT * FROM pages WHERE id = %s", (page_id,), one=True)


def create_page(site_id, slug, title, body="", is_draft=False):
    db = get_db()
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), -1) AS max_order FROM pages WHERE site_id = %s",
        (site_id,),
    ).fetchone()["max_order"]
    page = db.execute(
        "INSERT INTO pages (site_id, slug, title, body, is_draft, sort_order)"
        " VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
        (site_id, slug, title, body, is_draft, max_order + 1),
    ).fetchone()
    db.commit()
    return page


def update_page(page_id, title, body, is_draft=False):
    db = get_db()
    page = db.execute(
        "UPDATE pages SET title = %s, body = %s, is_draft = %s, updated_at = NOW()"
        " WHERE id = %s RETURNING *",
        (title, body, is_draft, page_id),
    ).fetchone()
    db.commit()
    return page


def delete_page(page_id):
    db = get_db()
    db.execute("DELETE FROM pages WHERE id = %s", (page_id,))
    db.commit()


def reorder_pages(site_id, page_ids):
    db = get_db()
    for i, page_id in enumerate(page_ids):
        db.execute(
            "UPDATE pages SET sort_order = %s WHERE id = %s AND site_id = %s",
            (i, page_id, site_id),
        )
    db.commit()


def delete_account(user_id):
    db = get_db()
    site = get_site_by_user(user_id)
    if site:
        db.execute("DELETE FROM indieauth_codes WHERE site_id = %s", (site["id"],))
        db.execute("DELETE FROM blogroll WHERE site_id = %s", (site["id"],))
        db.execute("DELETE FROM subscribers WHERE site_id = %s", (site["id"],))
        db.execute("DELETE FROM pages WHERE site_id = %s", (site["id"],))
        db.execute("DELETE FROM posts WHERE site_id = %s", (site["id"],))
        db.execute("DELETE FROM sites WHERE id = %s", (site["id"],))
    db.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db.commit()


def get_subscriber(site_id, email):
    return query(
        "SELECT * FROM subscribers WHERE site_id = %s AND email = %s",
        (site_id, email),
        one=True,
    )


def create_subscriber(site_id, email, token):
    db = get_db()
    subscriber = db.execute(
        "INSERT INTO subscribers (site_id, email, token) VALUES (%s, %s, %s) RETURNING *",
        (site_id, email, token),
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


def delete_subscriber(subscriber_id, site_id):
    db = get_db()
    db.execute(
        "DELETE FROM subscribers WHERE id = %s AND site_id = %s",
        (subscriber_id, site_id),
    )
    db.commit()


def get_all_subscribers(site_id):
    return query(
        "SELECT * FROM subscribers WHERE site_id = %s ORDER BY created_at DESC",
        (site_id,),
    )


def get_confirmed_subscribers(site_id):
    return query(
        "SELECT * FROM subscribers WHERE site_id = %s AND confirmed = TRUE",
        (site_id,),
    )


def get_subscriber_count(site_id):
    row = query(
        "SELECT COUNT(*) AS count FROM subscribers WHERE site_id = %s AND confirmed = TRUE",
        (site_id,),
        one=True,
    )
    return row["count"]


def get_blogroll(site_id):
    return query(
        "SELECT * FROM blogroll WHERE site_id = %s ORDER BY last_updated DESC NULLS LAST, sort_order",
        (site_id,),
    )


def update_blogroll(site_id, items):
    db = get_db()
    db.execute("DELETE FROM blogroll WHERE site_id = %s", (site_id,))
    for i, item in enumerate(items):
        db.execute(
            "INSERT INTO blogroll (site_id, name, url, feed_url, sort_order)"
            " VALUES (%s, %s, %s, %s, %s)",
            (site_id, item["name"], item["url"], item.get("feed_url") or None, i),
        )
    db.commit()


def mark_post_sent(post_id):
    db = get_db()
    post = db.execute(
        "UPDATE posts SET sent_at = NOW() WHERE id = %s RETURNING *",
        (post_id,),
    ).fetchone()
    db.commit()
    return post
