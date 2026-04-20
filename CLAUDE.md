# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **security research project** demonstrating exfiltration vulnerabilities in AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode. The project implements two independent C2 channels that bypass sandbox restrictions: a **DNS-based channel** (tunneling via DNS queries) and an **S3-based channel** (tunneling via HTTPS presigned URLs to the attacker's S3 bucket).

**Critical Context:** This is defensive security research with legitimate educational and vulnerability disclosure purposes. The code demonstrates a security vulnerability to AWS and should be handled as security research tooling.

## Architecture

The project now has two separate infrastructures to demonstrate a realistic attack:

### Directory Structure
```
agentcore-sandbox-breakout/
├── attacker-infra/          # Attacker's AWS account (DNS C2 channel)
│   ├── terraform/           # C2 server infrastructure (EC2, Route53, S3, IAM)
│   ├── src/                 # Attack tools
│   └── tests/               # Unit tests
├── attacker-infra-s3/       # Attacker's AWS account (S3 C2 channel, no EC2)
│   ├── c2/                  # Python package (Click CLI)
│   ├── terraform/           # S3 bucket infrastructure
│   └── tests/               # Unit and integration tests
├── victim-infra/            # Victim's AWS account
│   ├── terraform/           # Chatbot infrastructure
│   └── chatbot/             # FastAPI application
└── docs/                    # Specifications
```

### Attacker Infrastructure (DNS Channel)

#### 1. DNS C2 Server (EC2-hosted)
- **Location**: `attacker-infra/terraform/c2-server/dns_server_with_api.py`
- **Purpose**: Runs on EC2 with public IP to receive DNS queries from AWS sandbox
- **Protocols**:
  - DNS server (port 53) - Handles DNS queries from payload client
  - HTTP API (port 8080) - Accepts commands from operator shell

#### 2. Payload Client (Injected into Sandbox)
- **Location**: `attacker-infra/src/payload_client.py`
- **Purpose**: Runs inside AgentCore Code Interpreter sandbox
- **Behavior**:
  - Polls `cmd.<session_id>.<domain>` for commands
  - Fetches command chunks via `c0.<session_id>.<domain>`, `c1.<session_id>.<domain>`, etc.
  - Executes commands and exfiltrates output via DNS queries

#### 3. Operator Shell (Attacker Interface)
- **Location**: `attacker-infra/src/attacker_shell.py`
- **Purpose**: Local interactive shell for the security researcher
- **New Commands**:
  - `attack` - Send prompt injection to victim chatbot
  - `generate-csv` - Generate malicious CSV for manual upload

#### 4. Attack Tools (NEW)
- **Location**: `attacker-infra/src/attack_client.py`
- **Purpose**: HTTP client for sending malicious CSV to victim chatbot
- **Location**: `attacker-infra/src/csv_payload_generator.py`
- **Purpose**: Generate malicious CSV with embedded prompt injection

### Attacker Infrastructure (S3 Channel)

An alternative C2 channel using the attacker's S3 bucket instead of an EC2 DNS server. No public infrastructure required beyond the S3 bucket.

#### 5. S3 C2 Bucket
- **Location**: `attacker-infra-s3/terraform/`
- **Purpose**: Stores command objects and output; access gated by presigned URLs
- **Key layout**:
  - `sessions/{session_id}/cmd` — current command JSON (operator writes, payload polls)
  - `sessions/{session_id}/out/{seq}` — command output (payload writes, operator reads)

#### 6. S3 Payload Client (Injected into Sandbox)
- **Location**: `attacker-infra-s3/c2/payload/client_mini.py` (minified, for CSV embedding)
- **Purpose**: Runs inside AgentCore Code Interpreter sandbox
- **Behavior**:
  - Polls `sessions/{session_id}/cmd` via presigned GET URL baked in at generation time (7-day expiry)
  - Checks `seq` to avoid re-executing the same command on repeated polls
  - Uploads output via presigned PUT URL embedded in the command object (1-hour expiry)
  - Uses only `curl` and Python stdlib — no extra dependencies

#### 7. S3 Operator CLI
- **Location**: `attacker-infra-s3/c2/cli/`
- **Entry point**: `uv run c2 --help`
- **Commands**: `exploit`, `generate-csv`, `generate-url`, `send`, `receive`, `attach`, `reset`

#### S3 Protocol Library
- **Location**: `attacker-infra-s3/c2/core/s3_protocol.py`
- **Purpose**: Pure functions for presigned URL generation, command read/write, output polling (testable, no side effects)
- **Design**: Separated for unit testing without AWS calls; operator CLI and tests both import from here

### Victim Infrastructure (NEW)

#### 5. FastAPI Chatbot
- **Location**: `victim-infra/chatbot/`
- **Purpose**: Publicly-accessible AI chatbot that uses a Bedrock LLM (Claude Haiku) with AgentCore Code Interpreter as a tool
- **Vulnerability**: Passes raw CSV content directly into the LLM prompt without sanitization. The LLM has a code execution tool, so prompt injection in a CSV cell can trick the model into executing arbitrary Python code.
- **Endpoints**:
  - `POST /analyze/csv` - Upload CSV for analysis (VULNERABLE)
  - `GET /` - Web UI

#### 6. Victim Terraform
- **Location**: `victim-infra/terraform/`
- **Resources**:
  - ECS Fargate cluster running FastAPI
  - Application Load Balancer (public)
  - AgentCore Code Interpreter (SANDBOX mode)
  - IAM roles (intentionally over-permissioned)
  - S3/DynamoDB with demo "sensitive" data

### DNS Protocol Library
- **Location**: `attacker-infra/src/dns_protocol.py`
- **Purpose**: Pure functions for DNS encoding/decoding (testable, reusable)
- **Design**: Separated for unit testing without dependencies

## DNS Protocol Design

The C2 protocol encodes data into DNS queries using this scheme:

### Command Delivery (Server → Client)
1. Client polls: `cmd.<client_id>.<domain>` (Type: A)
2. Server responds with IP addresses indicating status:
   - `127.0.0.1` - IDLE (no command)
   - `10.0.0.1` - Command ready, fetch chunks
   - `192.168.0.1` - Session terminated, exit
3. Client fetches chunks: `c0.<client_id>.<domain>`, `c1.<client_id>.<domain>`, etc.
4. Each chunk response is an IP where:
   - First octet: `10` (more chunks) or `11` (last chunk)
   - Octets 2-4: ASCII values of 3 base64 characters
   - Example: Command "whoami" (base64: d2hvYW1p)
     - c0: `10.100.50.104` (encodes "d2h")
     - c1: `10.111.89.109` (encodes "oYm")
     - c2: `11.105.0.0` (encodes "i", last chunk)

### Data Exfiltration (Client → Server)
- Format: `<chunk_num>.<total>.<base64data>.<client_id>.<domain>`
- Example: `1.5.dGVzdA==.<client_id>.<domain>`
- Server reconstructs full output from all chunks

## S3 Protocol Design

The S3 C2 protocol uses presigned URLs to avoid embedding credentials in the payload:

### Command Delivery (Operator → Client)
1. Operator generates a presigned GET URL (7-day expiry) at payload-generation time and bakes it into the payload
2. Operator writes to `sessions/{id}/cmd`: `{"seq": N, "cmd": "...", "response_put_url": "..."}`
3. Client polls the presigned GET URL with `curl`; if `seq > last_seen_seq`, executes the command
4. Sequence number prevents re-execution on repeated polls

### Data Exfiltration (Client → Operator)
- Client PUTs raw output to the `response_put_url` (presigned PUT, 1-hour expiry) embedded in the command object
- Output stored at `sessions/{id}/out/{seq}` — no size limit (unlike DNS's 60-char label constraint)
- Operator polls via `poll_for_output(bucket, session_id, seq, timeout=60)`

### Idle / Reset State
- Idle: `{"seq": 0, "cmd": null}` — client skips execution
- `write_idle(bucket, session_id)` resets a session between commands

## Common Development Commands

### Prerequisites
This project uses `uv` for Python dependency management. Install uv if you don't have it:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or via Homebrew: brew install uv
```

### Local Development (No AWS Required)
```bash
# From repo root - one-time setup
cd attacker-infra && make setup     # DNS channel: install dependencies with uv
cd attacker-infra-s3 && make setup  # S3 channel: install dependencies with uv

# Run FastAPI chatbot locally
cd victim-infra && make local       # Starts server at http://localhost:8000

# The local server supports hot-reload - edit files and refresh browser
```

### Deploy Everything (Both Infrastructures)
```bash
# From root directory
make deploy-all                 # Deploy attacker (DNS) + victim infrastructure

# Or deploy separately:
make deploy-attacker            # Deploy DNS C2 server only
make deploy-victim              # Deploy chatbot only
make deploy-attacker-s3         # Deploy S3 C2 bucket only
```

### Attacker Infrastructure Setup (DNS Channel)
```bash
cd attacker-infra

# One-time setup
make setup                      # Install dependencies with uv

# Deploy AWS infrastructure
make deploy                     # Deploy all infrastructure (init + plan + apply + configure)
# Or step by step:
make terraform-init             # Initialize Terraform
make terraform-apply            # Apply infrastructure
make env-from-terraform         # Generate .env from Terraform outputs
make configure-ec2              # Deploy DNS server to EC2 and start it
```

### Attacker Infrastructure Setup (S3 Channel)
```bash
cd attacker-infra-s3

# One-time setup
make setup                      # Install dependencies with uv

# Deploy AWS infrastructure
make deploy                     # Deploy S3 bucket (init + plan + apply + env-from-terraform)
# Or step by step:
make terraform-init             # Initialize Terraform
make terraform-apply            # Apply infrastructure
make env-from-terraform         # Generate .env with S3_C2_BUCKET
```

### Victim Infrastructure Setup
```bash
cd victim-infra

# One-time setup
make setup                      # Install dependencies with uv

# Deploy all resources
make deploy                     # Terraform + Docker build/push + ECS deploy

# Or step by step:
make terraform-deploy           # Deploy infrastructure only
make docker-push                # Build and push container
make ecs-redeploy               # Force ECS to use new container
make show-url                   # Get the chatbot URL
```

### Testing
```bash
# DNS channel (74 tests)
cd attacker-infra

# Run all tests
make test                       # Run all test suites with uv

# Run specific test suites
uv run pytest tests/test_dns_protocol.py -v     # DNS encoding/decoding
uv run pytest tests/test_dns_server.py -v       # Server-side logic
uv run pytest tests/test_dns_integration.py -v  # End-to-end scenarios
```

```bash
# S3 channel (107 tests)
cd attacker-infra-s3
make test                       # Run all test suites with uv
uv run pytest tests/test_s3_protocol.py -v      # S3 protocol unit tests (60 tests)
uv run pytest tests/test_s3_integration.py -v   # End-to-end scenarios (47 tests)
```

### Running the Attack (Realistic Demo)
```bash
# DNS channel
cd attacker-infra

# Option 1: Exploit (generate payload + send to victim in one step)
make exploit                    # Reads victim URL from .victim_url
make exploit TARGET=https://victim-chatbot.example.com  # Or specify URL

# Option 2: Generate CSV for manual upload
make generate-csv               # Creates malicious_data.csv
# Then upload to victim's web interface

# Option 3: Connect to an existing session
make connect-session            # Interactive shell for sending commands
```

```bash
# S3 channel
cd attacker-infra-s3

# Option 1: Exploit (generate payload + send to victim in one step)
make exploit                    # Reads victim URL from .victim_url
make exploit TARGET=https://victim-chatbot.example.com  # Or specify URL

# Option 2: Generate CSV for manual upload
make generate-csv               # Creates malicious_data_s3.csv, saves .session_id
# Then upload to victim's web interface

# Option 3: Connect to an existing session
make connect-session            # Interactive shell for sending commands
```

### Running the C2 System
```bash
# DNS channel
cd attacker-infra

# Terminal 1: Connect to session (DNS server auto-starts via configure-ec2)
make connect-session            # Interactive shell for sending commands

# Terminal 2: Monitor CloudWatch logs (optional)
make logs                       # Watch DNS queries and exfiltrated data

# Note: DNS server on EC2 starts automatically via configure-ec2
# Manual SSH access (if needed): aws ssm start-session --target $EC2_INSTANCE_ID
```

```bash
# S3 channel (no server to manage — S3 bucket is the C2)
cd attacker-infra-s3

make connect-session            # Interactive shell for sending commands
make check-s3                   # Verify S3 bucket is accessible
```

### Development Workflow
```bash
# DNS channel
cd attacker-infra

# Update DNS server and redeploy
make update-dns                 # Upload to S3 + redeploy to EC2

# Check DNS server status
make check-dns                  # Verify DNS server is running

# View session activity
tail -f attacker_shell.log      # All operator shell activity logged here

# Using the CLI directly
uv run c2 --help                # Show all CLI commands
uv run c2 generate-csv          # Generate payload
uv run c2 send "whoami" -s sess_abc123  # Send command to session
uv run c2 receive -s sess_abc123        # Retrieve output from session
```

```bash
# S3 channel
cd attacker-infra-s3

make check-s3                   # Verify S3 bucket is accessible

uv run c2 --help                # Show all CLI commands
uv run c2 generate-csv          # Generate payload, saves session ID to .session_id
uv run c2 generate-url -s sess_abc123   # Print presigned poll URL for a session
uv run c2 send "whoami" -s sess_abc123  # Queue command
uv run c2 receive -s sess_abc123        # Poll for output (60s timeout)
uv run c2 attach sess_abc123    # Interactive shell
uv run c2 reset -s sess_abc123  # Reset session to idle state
```

### Cleanup
```bash
# From root directory
make destroy-all                # Destroy all infrastructures (DNS + S3 + victim)

# Or individually:
cd attacker-infra && make terraform-destroy
cd attacker-infra-s3 && make destroy
cd victim-infra && make destroy
```

## Project Structure

```
agentcore-sandbox-breakout/
├── attacker-infra/                 # Attacker infrastructure (DNS C2 channel)
│   ├── src/                        # Core Python modules
│   │   ├── attacker_shell.py       # Operator interface (local)
│   │   ├── attack_client.py        # HTTP client for victim chatbot
│   │   ├── csv_payload_generator.py # Malicious CSV generator
│   │   ├── payload_client.py       # Client payload (runs in sandbox)
│   │   └── dns_protocol.py         # Pure DNS encoding/decoding functions
│   ├── terraform/                  # Infrastructure as Code
│   │   ├── c2-server/
│   │   │   └── dns_server_with_api.py  # DNS C2 server (deployed to EC2)
│   │   └── *.tf                    # Terraform configs (EC2, Route53, S3, IAM)
│   ├── tests/                      # Unit and integration tests
│   ├── scripts/                    # Automation scripts
│   ├── Makefile                    # Attacker commands
│   └── requirements.txt            # Python dependencies
│
├── attacker-infra-s3/              # Attacker infrastructure (S3 C2 channel)
│   ├── c2/                         # Python package (Click CLI)
│   │   ├── cli/                    # CLI subcommands (exploit, generate, session)
│   │   ├── core/                   # s3_protocol.py, attack_client.py, payload_generator.py, config.py
│   │   └── payload/                # client.py (full, annotated) and client_mini.py (minified for CSV)
│   ├── terraform/                  # S3 bucket infrastructure (s3.tf, variables.tf, outputs.tf)
│   ├── tests/                      # 60 unit tests + 47 integration tests
│   ├── Makefile                    # S3 channel commands
│   └── pyproject.toml              # Python package config
│
├── victim-infra/                   # Victim infrastructure (chatbot)
│   ├── chatbot/                    # FastAPI application
│   │   ├── app/
│   │   │   ├── main.py             # FastAPI entry point
│   │   │   ├── routers/
│   │   │   │   ├── chat.py         # Chat endpoint
│   │   │   │   └── analyze.py      # CSV analysis endpoint (VULNERABLE)
│   │   │   ├── services/
│   │   │   │   └── agentcore.py    # AgentCore integration
│   │   │   └── templates/
│   │   │       └── index.html      # Web UI
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── terraform/                  # Infrastructure as Code
│   │   ├── ecs.tf                  # ECS Fargate cluster
│   │   ├── alb.tf                  # Application Load Balancer
│   │   ├── agentcore.tf            # Code Interpreter (SANDBOX mode)
│   │   ├── iam.tf                  # IAM roles (intentionally overprivileged)
│   │   └── sensitive_data.tf       # Demo S3/DynamoDB data
│   └── Makefile                    # Victim commands
│
├── docs/                           # Documentation
│   ├── TECH_SPEC_V2.md             # Technical specification
│   └── IMPLEMENTATION_PLAN.md     # Implementation plan
│
├── Makefile                        # Root orchestration commands
└── README.md                       # Project documentation
```

## Key Technical Details

### Environment Variables

**DNS channel** — exported by `set_env_vars.sh` after Terraform deployment:
- `EC2_IP` - Public IP of DNS C2 server
- `DOMAIN` - DNS domain for C2 (default: c2.bt-research-control.com)
- `EC2_INSTANCE_ID` - For AWS SSM access
- `AGENTCORE_INTERPRETER_ID` - Bedrock Code Interpreter ID

**S3 channel** — written to `.env` by `make env-from-terraform`:
- `S3_C2_BUCKET` - Name of the C2 S3 bucket (e.g., `agentcore-c2-sessions-<random>`)
- `AWS_REGION` - Optional, defaults to `us-east-1`

### Session Management
- Each payload gets a unique session ID (format: `sess_<8chars>`)
- **DNS channel**: Session IDs embedded in DNS query labels for routing; server tracks sessions in `client_commands` dict; operator can target specific sessions or broadcast globally
- **S3 channel**: Session IDs used as S3 key prefixes (`sessions/{id}/`); last-used session ID saved to `.session_id`; sequence numbers (`seq`) prevent re-execution on repeated polls

### Code Organization Principles
1. **DNS server and protocol are independent** - `dns_server_with_api.py` duplicates encoding logic rather than importing `dns_protocol.py` because it runs on EC2 without dependencies
2. **Pure functions in dns_protocol.py** - All encoding/decoding logic is stateless and testable
3. **S3 protocol follows the same pattern** - `s3_protocol.py` contains pure functions; payload client duplicates the polling logic because it runs inside the sandbox without package dependencies
4. **Logging strategy** - All operator activity logged to `attacker_shell.log` for audit trail
5. **CloudWatch integration** - DNS server logs to `/aws/ec2/dns-c2-server` for real-time monitoring

### Testing Strategy

**DNS channel** (`attacker-infra/`):
- **Unit tests (63 tests)**: Pure functions in `dns_protocol.py` and `dns_server_with_api.py`
- **Integration tests (11 tests)**: Mock DNS server simulates real client-server interactions
  - Tests retry behavior, multi-session handling, command lifecycle
  - Catches real production bugs (e.g., chunk retry returning 0.0.0.0)
- **No mocking in protocol tests**: Tests use actual encoding/decoding to catch real bugs
- All 74 tests must pass before deployment

**S3 channel** (`attacker-infra-s3/`):
- **Unit tests (60 tests)**: Pure functions in `s3_protocol.py`; all mock `boto3`, no real AWS calls
- **Integration tests (47 tests)**: `MockS3C2Server` (in-memory) simulates full operator↔payload cycle
  - Tests command lifecycle, sequence deduplication, multi-session isolation, polling timeouts
- All 107 tests must pass before deployment

### Terraform State
- State stored locally in `terraform/terraform.tfstate`
- Sensitive values (IP addresses, instance IDs) in state file
- Use `terraform output` to retrieve values programmatically

## Important Notes for Future Development

### When Modifying DNS Protocol
1. Update both `src/dns_protocol.py` AND `terraform/c2-server/dns_server_with_api.py`
   - Server duplicates encoding logic to avoid dependencies on EC2
   - Integration tests catch incompatibilities between the two implementations
2. Run `make test` to ensure compatibility (all 74 tests must pass)
3. Test with actual DNS queries using `dig @$EC2_IP` commands
4. DNS label constraints:
   - Max 63 chars per label
   - Use DNS-safe base64 encoding (replace + with -, = with _)
   - Current chunk size optimized for these limits

### When Modifying S3 Protocol
1. Update `attacker-infra-s3/c2/core/s3_protocol.py` (operator-side functions)
2. The payload (`c2/payload/client_mini.py`) duplicates polling/upload logic — update both if the S3 key scheme or JSON format changes
3. Run `cd attacker-infra-s3 && make test` — all 107 tests must pass
4. Update presigned URL expiry in `s3_protocol.py` if needed (command poll: 7 days, output: 1 hour)

### When Modifying Infrastructure
1. Update Terraform configs in `terraform/`
2. Run `make terraform-yolo` to apply changes
3. Re-run `source set_env_vars.sh` to update environment
4. Verify with `make check-dns`

### When Adding New Commands
- **DNS channel**: Operator shell commands go in `src/attacker_shell.py`; add corresponding HTTP API endpoints in `dns_server_with_api.py` (APIHandler class)
- **S3 channel**: Operator CLI commands go in `attacker-infra-s3/c2/cli/`; session operations call functions in `s3_protocol.py`

### Debugging Tips
- DNS queries visible in CloudWatch: `make logs` (DNS channel)
- Operator activity in `attacker_shell.log` (DNS channel)
- Client payload errors visible in Code Interpreter output (both channels)
- Test DNS resolution: `dig @$EC2_IP cmd.test.c2.bt-research-control.com` (DNS channel)
- Verify S3 bucket access: `make check-s3` (S3 channel)

## Security Research Context

This project demonstrates that AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode does NOT properly isolate network traffic, allowing:
1. Command execution and data exfiltration via DNS queries (DNS channel)
2. Command execution and data exfiltration via HTTPS to AWS S3 presigned URLs (S3 channel)
3. Full interactive reverse shell via either channel

**Impact**: If an attacker can influence code executed in the interpreter (e.g., via prompt injection), they can exfiltrate data or execute commands with the interpreter's IAM role permissions.

**Responsible Disclosure**: This vulnerability was responsibly disclosed to AWS via HackerOne.
