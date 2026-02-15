from models import query, execute, get_db


def subdomain_taken(subdomain):
    return query("SELECT id FROM sites WHERE subdomain = %s", (subdomain,), one=True)


def create_user_and_site(email, subdomain):
    db = get_db()
    user = db.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (email,)).fetchone()
    site = db.execute("INSERT INTO sites (subdomain, user_id, title) VALUES (%s, %s, %s) RETURNING id",
                      (subdomain, user["id"], subdomain)).fetchone()
    db.commit()
    return user, site
