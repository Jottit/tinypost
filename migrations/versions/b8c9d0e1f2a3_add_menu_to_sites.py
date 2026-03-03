"""add menu to sites

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-03-03 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE sites ADD COLUMN IF NOT EXISTS menu TEXT")
    op.execute("""
        UPDATE sites SET menu = (
            SELECT string_agg(title, E'\n' ORDER BY sort_order)
            FROM pages WHERE pages.site_id = sites.id AND NOT is_draft
        )
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE sites DROP COLUMN IF EXISTS menu")
