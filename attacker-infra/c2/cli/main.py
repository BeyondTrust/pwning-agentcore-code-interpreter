"""Main CLI entry point for C2 toolkit."""

import click

from c2.core.config import get_config

from .attack import attack
from .exploit import exploit
from .generate import generate_csv
from .session import attach, debug, receive, send, sessions, status


@click.group()
@click.version_option(package_name="c2")
@click.pass_context
def cli(ctx):
    """
    DNS C2 Toolkit - Command & Control for AgentCore sandbox breakout demo.

    \b
    Quick start:
      c2 exploit                               Generate + send payload
      c2 exploit https://victim-chatbot.com     Launch attack against URL
      c2 attach sess_xxx                        Interactive C2 shell
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = get_config()


# Register commands
cli.add_command(exploit)
cli.add_command(attack)
cli.add_command(send)
cli.add_command(receive)
cli.add_command(attach)
cli.add_command(status)
cli.add_command(sessions)
cli.add_command(debug)
cli.add_command(generate_csv)


if __name__ == "__main__":
    cli()
