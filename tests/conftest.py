import os

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from app import app

TEST_DB = "tinypost_test"


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    conn = psycopg.connect("dbname=postgres", autocommit=True)
    conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
    conn.execute(f"CREATE DATABASE {TEST_DB}")
    conn.close()

    os.environ["DATABASE_URL"] = f"postgresql://localhost/{TEST_DB}"
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    yield

    conn = psycopg.connect("dbname=postgres", autocommit=True)
    conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
    conn.close()


@pytest.fixture(autouse=True)
def clean_tables():
    conn = psycopg.connect(f"dbname={TEST_DB}")
    conn.execute("DELETE FROM indieauth_codes")
    conn.execute("DELETE FROM blogroll")
    conn.execute("DELETE FROM feeds")
    conn.execute("DELETE FROM subscribers")
    conn.execute("DELETE FROM posts")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["DATABASE"] = TEST_DB
    app.config["SERVER_NAME"] = app.config["BASE_DOMAIN"]
    from app import limiter

    limiter.enabled = False
    with app.test_client() as client:
        yield client


SITE_HOST = "myblog.tinypost.localhost:8000"


@pytest.fixture
def owner(client):
    from db import create_user

    with app.app_context():
        user = create_user("owner@example.com", "myblog")
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
    return user


@pytest.fixture
def taken_subdomain(client):
    from db import create_user

    with app.app_context():
        create_user("taken@example.com", "taken")
    return "taken"
