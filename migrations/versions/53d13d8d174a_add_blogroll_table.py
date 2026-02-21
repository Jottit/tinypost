"""add blogroll table

Revision ID: 53d13d8d174a
Revises: 9b3ddbaaf5f0
Create Date: 2026-02-21 14:50:07.426771

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "53d13d8d174a"
down_revision: Union[str, Sequence[str], None] = "9b3ddbaaf5f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS blogroll (
            id SERIAL PRIMARY KEY,
            site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            feed_url TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.drop_table("blogroll")
