"""add published_at to posts

Revision ID: 9b3ddbaaf5f0
Revises: a1b2c3d4e5f6
Create Date: 2026-02-20 16:15:26.906730

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b3ddbaaf5f0"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE posts SET published_at = created_at")


def downgrade() -> None:
    op.drop_column("posts", "published_at")
