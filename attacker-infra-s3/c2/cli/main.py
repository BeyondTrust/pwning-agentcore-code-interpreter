"""Main CLI entry point for S3 C2 toolkit."""

import click

from .exploit import exploit
from .generate import generate_csv, generate_url
from .session import attach, receive, reset, send


@click.group()
@click.version_option(package_name="c2")
def cli():
    """
    S3 C2 Toolkit — presigned URL transport, no EC2 required.
    \b
    Quick start:
      c2 exploit                                Generate + send payload
      c2 exploit https://victim-chatbot.com     Launch attack against URL
      c2 attach sess_xxx                        Interactive C2 shell
    """
    pass


cli.add_command(exploit)
cli.add_command(send)
cli.add_command(receive)
cli.add_command(generate_csv)
cli.add_command(generate_url)
cli.add_command(reset)
cli.add_command(attach)


if __name__ == "__main__":
    cli()
