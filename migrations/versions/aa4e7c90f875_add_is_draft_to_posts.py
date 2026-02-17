"""add is_draft to posts

Revision ID: aa4e7c90f875
Revises:
Create Date: 2026-02-17 13:52:43.935277

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa4e7c90f875"
down_revision: Union[str, Sequence[str], None] = "initial0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )


def downgrade() -> None:
    op.drop_column("posts", "is_draft")
