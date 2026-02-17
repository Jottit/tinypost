"""add design column to sites

Revision ID: b3f1a2c4d5e6
Revises: aa4e7c90f875
Create Date: 2026-02-17 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "b3f1a2c4d5e6"
down_revision: Union[str, Sequence[str], None] = "aa4e7c90f875"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sites", sa.Column("design", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("sites", "design")
