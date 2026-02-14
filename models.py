import os
import psycopg
from psycopg.rows import dict_row
from flask import g

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/jottit")


def get_db():
    if "db" not in g:
        g.db = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    db.execute(sql, args)
    db.commit()
