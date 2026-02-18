"""merge license and pages

Revision ID: e3f4a5b6c7d8
Revises: c1a2b3c4d5e6, d2e3f4a5b6c7
Create Date: 2026-02-18 19:30:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = ("c1a2b3c4d5e6", "d2e3f4a5b6c7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
