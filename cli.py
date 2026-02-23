import click


def init_cli(app):
    @app.cli.command("refresh-feeds")
    @click.argument("url", required=False)
    def refresh_feeds_command(url):
        """Fetch RSS/Atom feeds and update blogroll metadata.

        Optionally pass a URL to refresh only matching blogroll entries.
        """
        from feed_fetcher import refresh_all_feeds

        if url:
            click.echo(f"Refreshing feeds matching {url}...")
        else:
            click.echo("Refreshing all feeds...")
        refresh_all_feeds(url=url)
        click.echo("Done.")
