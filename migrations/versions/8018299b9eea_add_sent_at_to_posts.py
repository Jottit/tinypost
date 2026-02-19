"""add sent_at to posts

Revision ID: 8018299b9eea
Revises: 35e5dc07b8e9
Create Date: 2026-02-19 15:59:36.141837

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8018299b9eea"
down_revision: Union[str, Sequence[str], None] = "35e5dc07b8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("posts", "sent_at")
