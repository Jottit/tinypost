"""merge sites into users

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to users
    op.add_column("users", sa.Column("subdomain", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("title", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("avatar", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("custom_domain", sa.Text(), nullable=True))
    op.add_column(
        "users", sa.Column("domain_verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("users", sa.Column("domain_verification_token", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("license", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("links", sa.JSON(), nullable=True, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("users", sa.Column("theme", sa.Text(), nullable=True))

    # 2. Copy data from sites
    op.execute("""
        UPDATE users SET
            subdomain = s.subdomain,
            title = s.title,
            bio = s.bio,
            avatar = s.avatar,
            custom_domain = s.custom_domain,
            domain_verified_at = s.domain_verified_at,
            domain_verification_token = s.domain_verification_token,
            license = s.license,
            links = COALESCE(s.social_links, '[]'::jsonb),
            theme = s.design->>'preset'
        FROM sites s WHERE s.user_id = users.id
        """)

    # 3. Add user_id column to dependent tables
    for table in ("posts", "subscribers", "blogroll", "indieauth_codes"):
        op.add_column(table, sa.Column("user_id", sa.Integer(), nullable=True))
        op.execute(
            f"UPDATE {table} SET user_id = s.user_id FROM sites s WHERE {table}.site_id = s.id"
        )
        op.alter_column(table, "user_id", nullable=False)
        op.create_foreign_key(f"fk_{table}_user_id", table, "users", ["user_id"], ["id"])
        op.create_index(f"idx_{table}_user_id", table, ["user_id"])

    # 4. Recreate unique constraint on posts
    op.drop_constraint("posts_site_id_slug_key", "posts", type_="unique")
    op.create_unique_constraint("posts_user_id_slug_key", "posts", ["user_id", "slug"])

    # 5. Drop old site_id indexes
    for table in ("subscribers", "blogroll", "indieauth_codes"):
        op.drop_index(f"idx_{table}_site_id", table_name=table)

    # 6. Drop old site_id columns
    for table in ("posts", "subscribers", "blogroll", "indieauth_codes"):
        op.drop_column(table, "site_id")

    # 7. Make subdomain and title NOT NULL on users
    op.execute("UPDATE users SET subdomain = '' WHERE subdomain IS NULL")
    op.execute("UPDATE users SET title = subdomain WHERE title IS NULL")
    op.alter_column("users", "subdomain", nullable=False)
    op.alter_column("users", "title", nullable=False, server_default=sa.text("''"))
    op.create_unique_constraint("users_subdomain_key", "users", ["subdomain"])
    op.create_unique_constraint("users_custom_domain_key", "users", ["custom_domain"])

    # 8. Drop old tables
    op.drop_table("comments")
    op.drop_table("pages")
    op.drop_table("sites")


def downgrade() -> None:
    pass
