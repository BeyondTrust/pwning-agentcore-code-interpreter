"""
Mock S3 C2 Server for integration testing.

Replicates the in-memory behaviour of the S3 C2 channel without touching
real AWS resources, so integration tests can verify the full operator →
payload → operator command lifecycle.
"""

import json
from typing import Optional


class MockS3C2Server:
    """
    In-memory simulation of the S3 C2 channel.

    The real system uses two S3 key namespaces per session:
      sessions/{session_id}/cmd        – command JSON written by the operator
      sessions/{session_id}/out/{seq}  – output written by the payload client

    This mock replicates that layout in plain Python dicts so we can drive
    integration tests without any boto3 or network calls.
    """

    def __init__(self):
        # cmd store: session_id -> raw JSON string
        self._commands: dict[str, str] = {}
        # output store: (session_id, seq) -> decoded string
        self._outputs: dict[tuple, str] = {}

    # ------------------------------------------------------------------
    # Operator-side helpers
    # ------------------------------------------------------------------

    def write_command(
        self,
        session_id: str,
        seq: int,
        cmd: str,
        response_put_url: str = "https://mock-put.example.com/out",
    ) -> None:
        """Write a command JSON object to the session's cmd slot."""
        payload = json.dumps(
            {"seq": seq, "cmd": cmd, "response_put_url": response_put_url}
        )
        self._commands[session_id] = payload

    def write_idle(self, session_id: str) -> None:
        """Reset the session to idle (cmd=None, seq=0)."""
        self._commands[session_id] = json.dumps({"seq": 0, "cmd": None})

    def read_output(self, session_id: str, seq: int) -> Optional[str]:
        """Return exfiltrated output for the given session/seq, or None."""
        return self._outputs.get((session_id, seq))

    def get_state(self) -> dict:
        """Return a snapshot of internal state (for debugging tests)."""
        return {
            "commands": dict(self._commands),
            "outputs": {str(k): v for k, v in self._outputs.items()},
        }

    # ------------------------------------------------------------------
    # Payload-side helpers  (simulate what client_mini.py does)
    # ------------------------------------------------------------------

    def poll_command(self, session_id: str) -> Optional[dict]:
        """
        Simulate the payload polling the S3 cmd object.
        Returns the parsed command dict, or None if the key doesn't exist.
        """
        raw = self._commands.get(session_id)
        if raw is None:
            return None
        return json.loads(raw)

    def put_output(self, session_id: str, seq: int, data: str) -> None:
        """Simulate the payload uploading output via a presigned PUT URL."""
        self._outputs[(session_id, seq)] = data

    def simulate_payload_loop_once(self, session_id: str, last_seq: int = 0) -> int:
        """
        Run a single iteration of the payload's main loop for one session.

        Mirrors the logic in client_mini.py:
          1. Poll for command JSON
          2. Skip if no cmd or seq <= last seen seq
          3. 'Execute' by returning a canned result string
          4. Upload output

        Returns the new last_seq value so callers can track execution state.
        """
        obj = self.poll_command(session_id)
        if obj is None:
            return last_seq

        cmd = obj.get("cmd")
        seq = obj.get("seq", 0)
        response_put_url = obj.get("response_put_url")

        if not cmd or seq <= last_seq:
            return last_seq

        # Simulate execution: produce deterministic output for testing
        out = f"output_of: {cmd}"
        self.put_output(session_id, seq, out)
        return seq
