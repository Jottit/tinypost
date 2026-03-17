"""add billing columns to users

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-03-16 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h4i5j6k7l8m9"
down_revision: Union[str, Sequence[str], None] = "g3h4i5j6k7l8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
    )
    op.add_column("users", sa.Column("plan_expires_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "plan_expires_at")
    op.drop_column("users", "plan")
