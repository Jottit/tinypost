"""create initial tables

Revision ID: initial0001
Revises:
Create Date: 2026-02-17 13:56:54.802309

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "initial0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            subdomain TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            bio TEXT,
            avatar TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            site_id INTEGER NOT NULL REFERENCES sites(id),
            slug TEXT NOT NULL,
            title TEXT,
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(site_id, slug)
        )
    """)


def downgrade() -> None:
    op.drop_table("posts")
    op.drop_table("sites")
    op.drop_table("users")
