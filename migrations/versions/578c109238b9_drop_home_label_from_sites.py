"""drop home_label from sites

Revision ID: 578c109238b9
Revises: 6898b665d726
Create Date: 2026-02-20 00:05:10.186935

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "578c109238b9"
down_revision: Union[str, Sequence[str], None] = "6898b665d726"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("sites", "home_label")


def downgrade() -> None:
    op.add_column(
        "sites",
        sa.Column("home_label", sa.Text(), nullable=False, server_default="Home"),
    )
