"""add latest_post_url to blogroll

Revision ID: 2141fe515ff4
Revises: a556473bba0f
Create Date: 2026-02-23 16:48:31.220223

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2141fe515ff4"
down_revision: Union[str, Sequence[str], None] = "a556473bba0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("blogroll", sa.Column("latest_post_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("blogroll", "latest_post_url")
