# Plan: Demo Narration & UX Improvements

## Context

The C2 exploit flow works end-to-end but feels "magical" during a live demo. After `c2 exploit` delivers the payload, there's a 10-60s dead gap before the payload calls home with zero feedback. The audience sees silence and doesn't understand the attack chain. The `c2 attach` command-wait loop also shows no progress. The goal is to add narration, progress indicators, and auto-wait-for-session so a presenter can walk through the flow with the audience following along.

## Design Decisions

- **Auto-wait-for-session is default** (`--no-wait` to disable). The dead gap is bad UX even outside demos.
- **`--narrate` is opt-in** — adds `[~]` prefixed explanation lines explaining each step for the audience.
- **No narration inside `attach`** — the shell is already interactive; narration would clutter command output.
- **`[~]` prefix** for narration lines — visually distinct from `[*]` (info), `[+]` (success), `[!]` (error), `[>]` (send).
- **`\r` progress dots** for the wait loops — cleaner than a progress bar for open-ended polling.

## Changes

### 1. Convert `print()` to `click.echo()` in attack_client.py, add `narrate` param
**File:** `attacker-infra/c2/core/attack_client.py`

- Replace all `print()` with `click.echo()` for consistent output
- Add `narrate: bool = False` to `__init__`
- Add `_narrate(msg)` helper that prints `[~] {msg}` only when `self.narrate` is True
- Add narration at each step in `run_full_attack()`:
  - Before generate: `"Generating malicious CSV with embedded prompt injection..."`
  - After generate: `"CSV contains a base64-encoded Python payload in the Notes field of row 3"`
  - Before send: `"Sending CSV to victim chatbot — the LLM will read it and execute the payload"`
  - After delivery: `"The payload runs inside a Code Interpreter sandbox with only DNS access"`

### 2. Convert `print()` to `click.echo(err=True)` in session_manager.py
**File:** `attacker-infra/c2/core/session_manager.py`

- All error `print()` calls → `click.echo(..., err=True)` so errors go to stderr

### 3. Add `--narrate`, `--wait/--no-wait`, `--wait-timeout` to exploit command
**File:** `attacker-infra/c2/cli/exploit.py`

- Add options: `--narrate` (default False), `--wait/--no-wait` (default True), `--wait-timeout` (default 60)
- Pass `narrate` to `AttackClient`
- After `run_full_attack()`, call `_wait_for_session(session_id, timeout, narrate)`:
  - Polls `SessionManager.list_sessions()` every 2s
  - Shows rolling `\r` progress: `[*] Waiting... 12s [........]`
  - On session found: `[+] Payload called home! (18s)`
  - With `--narrate`: adds `[~] Session active! Payload is polling every 3s from inside the sandbox`
  - On timeout: `[!] No session after 60s — payload may still arrive, check 'c2 sessions'`
  - `Ctrl+C` skips gracefully
- Add `import time` at top

### 4. Improve `attach` command-wait and `status` built-in
**File:** `attacker-infra/c2/cli/session.py`

**4a. Progress indicator** in the 30s command-wait loop inside `attach`:
- Replace silent `time.sleep(1)` with `\r` rolling dots: `[*] Waiting for output... 12s [......]`
- Print `\n` before output block to clear the progress line

**4b. Enhance `status` built-in** inside `attach`:
- Call `manager.list_sessions()` and find the current session
- Print liveness: `[*] Session sess_xxx: active (last seen 2.1s ago)` or `[!] Session not found in C2 server`
- Then show pending output (existing behavior)

### 5. `make demo` Makefile target
**File:** `attacker-infra/Makefile`

```makefile
demo:
	@if [ -n "$(TARGET)" ]; then \
		uv run c2 exploit $(TARGET) --narrate; \
	else \
		uv run c2 exploit --narrate; \
	fi
	@if [ -f .session_id ]; then \
		uv run c2 attach $$(cat .session_id); \
	fi
```

Add to `.PHONY` and `help`.

## File Summary

| File | Action |
|------|--------|
| `attacker-infra/c2/core/attack_client.py` | Edit (print→click.echo, add narrate) |
| `attacker-infra/c2/core/session_manager.py` | Edit (print→click.echo err=True) |
| `attacker-infra/c2/cli/exploit.py` | Edit (add options, _wait_for_session) |
| `attacker-infra/c2/cli/session.py` | Edit (progress indicator, enhanced status) |
| `attacker-infra/Makefile` | Edit (add demo target) |

## Verification

1. `make test` — all 74 tests pass
2. `uv run c2 exploit --help` shows new `--narrate`, `--wait/--no-wait`, `--wait-timeout` options
3. `uv run c2 exploit --narrate` prints `[~]` narration lines and auto-waits for session
4. `uv run c2 exploit --no-wait` skips session wait (old behavior)
5. `c2 attach` command-wait shows rolling dots with elapsed time
6. `status` inside `c2 attach` shows session liveness
7. `make demo` runs the full narrated flow
