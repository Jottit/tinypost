"""add feeds table and deduplicate blogroll

Revision ID: 815dc0f5998c
Revises: 2141fe515ff4
Create Date: 2026-02-23 18:16:16.106826

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "815dc0f5998c"
down_revision: Union[str, Sequence[str], None] = "2141fe515ff4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE feeds (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            feed_url TEXT,
            feed_title TEXT,
            feed_icon_url TEXT,
            latest_post_title TEXT,
            latest_post_url TEXT,
            last_updated TIMESTAMPTZ,
            last_fetched TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        INSERT INTO feeds (url, feed_url, feed_title, feed_icon_url,
                           latest_post_title, latest_post_url, last_updated, last_fetched)
        SELECT DISTINCT ON (url)
               url, feed_url, feed_title, feed_icon_url,
               latest_post_title, latest_post_url, last_updated, last_fetched
        FROM blogroll
        ORDER BY url, last_fetched DESC NULLS LAST
    """)

    op.add_column("blogroll", sa.Column("feed_id", sa.Integer(), nullable=True))

    op.execute("""
        UPDATE blogroll SET feed_id = feeds.id
        FROM feeds WHERE feeds.url = blogroll.url
    """)

    op.alter_column("blogroll", "feed_id", nullable=False)
    op.create_foreign_key("fk_blogroll_feed_id", "blogroll", "feeds", ["feed_id"], ["id"])

    op.drop_column("blogroll", "url")
    op.drop_column("blogroll", "feed_url")
    op.drop_column("blogroll", "feed_title")
    op.drop_column("blogroll", "feed_icon_url")
    op.drop_column("blogroll", "latest_post_title")
    op.drop_column("blogroll", "latest_post_url")
    op.drop_column("blogroll", "last_updated")
    op.drop_column("blogroll", "last_fetched")


def downgrade() -> None:
    op.add_column("blogroll", sa.Column("url", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("feed_url", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("feed_title", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("feed_icon_url", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("latest_post_title", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("latest_post_url", sa.Text(), nullable=True))
    op.add_column("blogroll", sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True))
    op.add_column("blogroll", sa.Column("last_fetched", sa.DateTime(timezone=True), nullable=True))

    op.execute("""
        UPDATE blogroll SET
            url = feeds.url,
            feed_url = feeds.feed_url,
            feed_title = feeds.feed_title,
            feed_icon_url = feeds.feed_icon_url,
            latest_post_title = feeds.latest_post_title,
            latest_post_url = feeds.latest_post_url,
            last_updated = feeds.last_updated,
            last_fetched = feeds.last_fetched
        FROM feeds WHERE feeds.id = blogroll.feed_id
    """)

    op.alter_column("blogroll", "url", nullable=False)
    op.drop_constraint("fk_blogroll_feed_id", "blogroll", type_="foreignkey")
    op.drop_column("blogroll", "feed_id")
    op.drop_table("feeds")
