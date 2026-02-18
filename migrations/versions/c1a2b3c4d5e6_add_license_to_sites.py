"""add license to sites

Revision ID: c1a2b3c4d5e6
Revises: bbcc42d2f54a
Create Date: 2026-02-18 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "bbcc42d2f54a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sites", sa.Column("license", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sites", "license")
