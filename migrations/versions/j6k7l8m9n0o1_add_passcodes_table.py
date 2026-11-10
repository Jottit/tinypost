"""add passcodes table

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-11-10 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j6k7l8m9n0o1"
down_revision: Union[str, Sequence[str], None] = "i5j6k7l8m9n0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "passcodes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purpose", sa.Text, nullable=False),
        sa.Column("passcode_hash", sa.Text, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_passcodes_user_id_purpose", "passcodes", ["user_id", "purpose"])


def downgrade() -> None:
    op.drop_index("idx_passcodes_user_id_purpose", table_name="passcodes")
    op.drop_table("passcodes")
