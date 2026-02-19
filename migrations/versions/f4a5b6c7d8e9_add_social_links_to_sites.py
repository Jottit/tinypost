"""add social_links to sites

Revision ID: f4a5b6c7d8e9
Revises: ec8b6e5b20c7
Create Date: 2026-02-19 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "8018299b9eea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sites", sa.Column("social_links", JSONB, server_default="[]"))


def downgrade() -> None:
    op.drop_column("sites", "social_links")
