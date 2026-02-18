"""add custom_css to sites

Revision ID: ec8b6e5b20c7
Revises: e3f4a5b6c7d8
Create Date: 2026-02-18 20:25:53.593739

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec8b6e5b20c7"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sites", sa.Column("custom_css", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sites", "custom_css")
