import pytest
import psycopg
from app import app

TEST_DB = "jottit_test"

@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    conn = psycopg.connect("dbname=postgres", autocommit=True)
    conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
    conn.execute(f"CREATE DATABASE {TEST_DB}")
    conn.close()

    conn = psycopg.connect(f"dbname={TEST_DB}")
    with open("schema.sql") as f:
        conn.execute(f.read())
    conn.commit()
    conn.close()

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
    with app.test_client() as client:
        yield client
