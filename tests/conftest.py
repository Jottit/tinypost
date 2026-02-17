import os

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from app import app

TEST_DB = "jottit_test"


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
    conn.execute("DELETE FROM posts")
    conn.execute("DELETE FROM sites")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["DATABASE"] = TEST_DB
    app.config["SERVER_NAME"] = app.config["BASE_DOMAIN"]
    with app.test_client() as client:
        yield client


@pytest.fixture
def taken_subdomain(client):
    from db import create_user_and_site

    with app.app_context():
        create_user_and_site("taken@example.com", "taken")
    return "taken"
