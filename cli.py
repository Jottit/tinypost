import click


def init_cli(app):
    @app.cli.command("refresh-feeds")
    def refresh_feeds_command():
        """Fetch RSS/Atom feeds and update blogroll metadata."""
        from feed_fetcher import refresh_all_feeds

        click.echo("Refreshing feeds...")
        refresh_all_feeds()
        click.echo("Done.")
