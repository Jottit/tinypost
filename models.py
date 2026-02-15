import os

import psycopg
from flask import current_app, g
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/jottit")


def get_db():
    if "db" not in g:
        db_name = current_app.config.get("DATABASE")
        dsn = f"dbname={db_name}" if db_name else DATABASE_URL
        g.db = psycopg.connect(dsn, row_factory=dict_row)
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
