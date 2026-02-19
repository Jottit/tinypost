"""add home_label to sites

Revision ID: 6898b665d726
Revises: f4a5b6c7d8e9
Create Date: 2026-02-19 22:56:17.854082

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6898b665d726"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sites",
        sa.Column("home_label", sa.Text(), nullable=False, server_default="Home"),
    )


def downgrade() -> None:
    op.drop_column("sites", "home_label")
