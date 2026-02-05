# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **security research project** demonstrating a DNS-based exfiltration vulnerability in AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode. The project implements a complete DNS-based command & control (C2) system that bypasses sandbox restrictions by tunneling commands and data through DNS queries.

**Critical Context:** This is defensive security research with legitimate educational and vulnerability disclosure purposes. The code demonstrates a security vulnerability to AWS and should be handled as security research tooling.

## Architecture

The project now has two separate infrastructures to demonstrate a realistic attack:

### Directory Structure
```
agentcore-sandbox-breakout/
├── attacker-infra/          # Attacker's AWS account
│   ├── terraform/           # C2 server infrastructure
│   ├── src/                 # Attack tools
│   └── tests/               # Unit tests
├── victim-infra/            # Victim's AWS account
│   ├── terraform/           # Chatbot infrastructure
│   └── chatbot/             # FastAPI application
└── docs/                    # Specifications
```

### Attacker Infrastructure

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

### Victim Infrastructure (NEW)

#### 5. FastAPI Chatbot
- **Location**: `victim-infra/chatbot/`
- **Purpose**: Publicly-accessible AI chatbot that uses AgentCore Code Interpreter
- **Vulnerability**: Passes user CSV content directly to Code Interpreter without sanitization
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
cd attacker-infra && make setup     # Install dependencies with uv

# Run FastAPI chatbot locally
cd victim-infra && make local       # Starts server at http://localhost:8000

# The local server supports hot-reload - edit files and refresh browser
```

### Deploy Everything (Both Infrastructures)
```bash
# From root directory
make deploy-all                 # Deploy attacker + victim infrastructure

# Or deploy separately:
make deploy-attacker            # Deploy C2 server only
make deploy-victim              # Deploy chatbot only
```

### Attacker Infrastructure Setup
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
cd attacker-infra

# Run all tests
make test                       # Run all test suites with uv

# Run specific test suites
uv run pytest tests/test_dns_protocol.py -v     # DNS encoding/decoding
uv run pytest tests/test_dns_server.py -v       # Server-side logic
uv run pytest tests/test_dns_integration.py -v  # End-to-end scenarios
```

### Running the Attack (Realistic Demo)
```bash
cd attacker-infra

# Option 1: Attack via HTTP (no victim credentials needed)
make attack TARGET=https://victim-chatbot.example.com

# Option 2: Generate CSV for manual upload
make generate-csv               # Creates malicious CSV file
# Then upload to victim's web interface

# Option 3: Direct Code Interpreter access (requires credentials)
make operator                   # Interactive shell for sending commands
```

### Running the C2 System
```bash
cd attacker-infra

# Terminal 1: Start operator shell (DNS server auto-starts via configure-ec2)
make operator                   # Interactive shell for sending commands

# Terminal 2: Monitor CloudWatch logs (optional)
make logs                       # Watch DNS queries and exfiltrated data

# Note: DNS server on EC2 starts automatically via configure-ec2
# Manual SSH access (if needed): aws ssm start-session --target $EC2_INSTANCE_ID
```

### Development Workflow
```bash
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

### Cleanup
```bash
# From root directory
make destroy-all                # Destroy both infrastructures

# Or individually:
cd attacker-infra && make terraform-destroy
cd victim-infra && make destroy
```

## Project Structure

```
agentcore-sandbox-breakout/
├── attacker-infra/                 # Attacker infrastructure (C2 server)
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
These are exported by `set_env_vars.sh` after Terraform deployment:
- `EC2_IP` - Public IP of DNS C2 server
- `DOMAIN` - DNS domain for C2 (default: c2.bt-research-control.com)
- `EC2_INSTANCE_ID` - For AWS SSM access
- `AGENTCORE_INTERPRETER_ID` - Bedrock Code Interpreter ID

### Session Management
- Each payload gets a unique session ID (format: `sess_<8chars>`)
- Session IDs are embedded in DNS queries for routing
- Server tracks sessions in `client_commands` dict
- Operator can target specific sessions or broadcast globally

### Code Organization Principles
1. **DNS server and protocol are independent** - `dns_server_with_api.py` duplicates encoding logic rather than importing `dns_protocol.py` because it runs on EC2 without dependencies
2. **Pure functions in dns_protocol.py** - All encoding/decoding logic is stateless and testable
3. **Logging strategy** - All operator activity logged to `attacker_shell.log` for audit trail
4. **CloudWatch integration** - DNS server logs to `/aws/ec2/dns-c2-server` for real-time monitoring

### Testing Strategy
- **Unit tests (63 tests)**: Pure functions in `dns_protocol.py` and `dns_server_with_api.py`
- **Integration tests (11 tests)**: Mock DNS server simulates real client-server interactions
  - Tests retry behavior, multi-session handling, command lifecycle
  - Catches real production bugs (e.g., chunk retry returning 0.0.0.0)
- **No mocking in protocol tests**: Tests use actual encoding/decoding to catch real bugs
- All 74 tests must pass before deployment

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

### When Modifying Infrastructure
1. Update Terraform configs in `terraform/`
2. Run `make terraform-yolo` to apply changes
3. Re-run `source set_env_vars.sh` to update environment
4. Verify with `make check-dns`

### When Adding New Commands
- Operator shell commands go in `src/attacker_shell.py`
- Add corresponding HTTP API endpoints in `dns_server_with_api.py` (APIHandler class)
- Update operator shell to call new API endpoints

### Debugging Tips
- DNS queries visible in CloudWatch: `make logs`
- Operator activity in `attacker_shell.log`
- Client payload errors visible in Code Interpreter output
- Test DNS resolution: `dig @$EC2_IP cmd.test.c2.bt-research-control.com`

## Security Research Context

This project demonstrates that AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode does NOT properly isolate from DNS, allowing:
1. Command execution via DNS TXT records
2. Data exfiltration via DNS query subdomains
3. Full interactive reverse shell via DNS tunneling

**Impact**: If an attacker can influence code executed in the interpreter (e.g., via prompt injection), they can exfiltrate data or execute commands with the interpreter's IAM role permissions.

**Responsible Disclosure**: This vulnerability was responsibly disclosed to AWS via HackerOne.
