from models import get_db, query


def subdomain_taken(subdomain):
    return query("SELECT id FROM sites WHERE subdomain = %s", (subdomain,), one=True)


def create_user_and_site(email, subdomain):
    db = get_db()
    user = db.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (email,)).fetchone()
    site = db.execute(
        "INSERT INTO sites (subdomain, user_id, title) VALUES (%s, %s, %s) RETURNING id",
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
