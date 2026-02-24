"""add comments table

Revision ID: a7b8c9d0e1f2
Revises: 815dc0f5998c
Create Date: 2026-02-24 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "815dc0f5998c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
            site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            name TEXT NOT NULL,
            email_hash TEXT NOT NULL,
            body TEXT NOT NULL,
            author_url TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        ALTER TABLE sites ADD COLUMN IF NOT EXISTS comments_enabled BOOLEAN NOT NULL DEFAULT TRUE
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE sites DROP COLUMN IF EXISTS comments_enabled")
    op.drop_table("comments")
