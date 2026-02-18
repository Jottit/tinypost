"""add pages table

Revision ID: d2e3f4a5b6c7
Revises: bbcc42d2f54a
Create Date: 2026-02-18 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "bbcc42d2f54a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
            site_id INTEGER NOT NULL REFERENCES sites(id),
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            is_draft BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(site_id, slug)
        )
    """)


def downgrade() -> None:
    op.drop_table("pages")
