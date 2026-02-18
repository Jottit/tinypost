"""add custom domain to sites

Revision ID: b3f1a2c4d567
Revises: aa4e7c90f875
Create Date: 2026-02-17 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f1a2c4d567"
down_revision: Union[str, Sequence[str], None] = "aa4e7c90f875"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sites", sa.Column("custom_domain", sa.Text(), nullable=True))
    op.add_column(
        "sites", sa.Column("domain_verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("sites", sa.Column("domain_verification_token", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_sites_custom_domain", "sites", ["custom_domain"])


def downgrade() -> None:
    op.drop_constraint("uq_sites_custom_domain", "sites")
    op.drop_column("sites", "domain_verification_token")
    op.drop_column("sites", "domain_verified_at")
    op.drop_column("sites", "custom_domain")
