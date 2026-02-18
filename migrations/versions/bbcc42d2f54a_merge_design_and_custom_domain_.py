"""merge design and custom domain migrations

Revision ID: bbcc42d2f54a
Revises: b3f1a2c4d567, b3f1a2c4d5e6
Create Date: 2026-02-18 12:41:01.957359

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "bbcc42d2f54a"
down_revision: Union[str, Sequence[str], None] = ("b3f1a2c4d567", "b3f1a2c4d5e6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
