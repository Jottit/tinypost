"""add foreign key indexes

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-03-03 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS idx_sites_user_id ON sites (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscribers_site_id ON subscribers (site_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_blogroll_site_id ON blogroll (site_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments (post_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_comments_site_id ON comments (site_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_indieauth_codes_site_id ON indieauth_codes (site_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_sites_user_id")
    op.execute("DROP INDEX IF EXISTS idx_subscribers_site_id")
    op.execute("DROP INDEX IF EXISTS idx_blogroll_site_id")
    op.execute("DROP INDEX IF EXISTS idx_comments_post_id")
    op.execute("DROP INDEX IF EXISTS idx_comments_site_id")
    op.execute("DROP INDEX IF EXISTS idx_indieauth_codes_site_id")
