"""add subscribers table

Revision ID: 35e5dc07b8e9
Revises: ec8b6e5b20c7
Create Date: 2026-02-19 15:42:46.864609

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "35e5dc07b8e9"
down_revision: Union[str, Sequence[str], None] = "ec8b6e5b20c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            site_id INTEGER NOT NULL REFERENCES sites(id),
            email TEXT NOT NULL,
            confirmed BOOLEAN NOT NULL DEFAULT FALSE,
            token TEXT NOT NULL UNIQUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.drop_table("subscribers")
