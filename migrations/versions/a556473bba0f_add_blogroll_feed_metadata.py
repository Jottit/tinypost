"""add blogroll feed metadata

Revision ID: a556473bba0f
Revises: 53d13d8d174a
Create Date: 2026-02-21 18:41:45.980781

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a556473bba0f"
down_revision: Union[str, Sequence[str], None] = "53d13d8d174a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("blogroll", sa.Column("feed_title", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("feed_icon_url", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("latest_post_title", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("last_fetched", sa.DateTime(timezone=True), nullable=True))
    op.add_column("blogroll", sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("blogroll", "last_updated")
    op.drop_column("blogroll", "last_fetched")
    op.drop_column("blogroll", "latest_post_title")
    op.drop_column("blogroll", "feed_icon_url")
    op.drop_column("blogroll", "feed_title")
