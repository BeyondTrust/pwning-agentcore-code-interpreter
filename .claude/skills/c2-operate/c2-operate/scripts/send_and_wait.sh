#!/bin/bash
# Non-interactive send+receive: sends a command and polls for output.
# Usage: send_and_wait.sh <session_id> <command> [timeout_seconds]
#
# Exit codes:
#   0 - output received
#   1 - timeout with no output
#   2 - failed to send command

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
ATTACKER_DIR="$PROJECT_ROOT/attacker-infra"

cd "$ATTACKER_DIR"

SESSION_ID="${1:?Usage: send_and_wait.sh <session_id> <command> [timeout]}"
COMMAND="${2:?Usage: send_and_wait.sh <session_id> <command> [timeout]}"
TIMEOUT="${3:-45}"

# Send command
if ! uv run c2 send "$COMMAND" -s "$SESSION_ID" 2>&1; then
    echo "[!] Failed to send command" >&2
    exit 2
fi

# Poll for output
uv run c2 receive -s "$SESSION_ID" --wait "$TIMEOUT" --poll-interval 2
