# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **security research project** demonstrating a DNS-based exfiltration vulnerability in AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode. The project implements a complete DNS-based command & control (C2) system that bypasses sandbox restrictions by tunneling commands and data through DNS queries.

**Critical Context:** This is defensive security research with legitimate educational and vulnerability disclosure purposes. The code demonstrates a security vulnerability to AWS and should be handled as security research tooling.

## Architecture

The system consists of three main components that work together:

### 1. DNS C2 Server (EC2-hosted)
- **Location**: `terraform/c2-server/dns_server_with_api.py`
- **Purpose**: Runs on EC2 with public IP to receive DNS queries from AWS sandbox
- **Protocols**:
  - DNS server (port 53) - Handles DNS queries from payload client
  - HTTP API (port 8080) - Accepts commands from operator shell
- **Key Functions**:
  - `encode_chunk_to_ip()` - Encodes 3 chars of base64 into IP address octets
  - `encode_command_to_chunks()` - Splits commands into DNS-deliverable chunks
  - `C2Resolver` class - Custom DNS resolver handling command delivery and data exfiltration

### 2. Payload Client (Injected into Sandbox)
- **Location**: `src/payload_client.py`
- **Purpose**: Runs inside AgentCore Code Interpreter sandbox
- **Behavior**:
  - Polls `cmd.<session_id>.<domain>` for commands
  - Fetches command chunks via `c0.<session_id>.<domain>`, `c1.<session_id>.<domain>`, etc.
  - Executes commands and exfiltrates output via DNS queries
  - Uses curl to trigger DNS queries with data embedded in subdomains

### 3. Operator Shell (Attacker Interface)
- **Location**: `src/attacker_shell.py`
- **Purpose**: Local interactive shell for the security researcher
- **Capabilities**:
  - Generate payloads with unique session IDs
  - Send commands to specific sessions via HTTP API
  - Retrieve command output from C2 server
  - Interactive mode for real-time interaction

### 4. DNS Protocol Library
- **Location**: `src/dns_protocol.py`
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

### Setup and Infrastructure
```bash
# One-time setup
make setup-env                  # Create Python venv
source venv/bin/activate        # Activate venv
make install                    # Install dependencies from requirements.txt

# Deploy AWS infrastructure
make terraform-yolo             # Deploy all infrastructure (init + plan + apply)
source set_env_vars.sh          # Export env vars (EC2_IP, DOMAIN, EC2_INSTANCE_ID)
make configure-ec2              # Deploy DNS server to EC2 and start it
```

### Testing
```bash
# Run all tests (protocol + server + integration)
make test                       # Run all three test suites
make test-verbose               # Verbose output with detailed assertions

# Run specific test suites (direct execution)
python3 tests/test_dns_protocol.py     # 36 tests - Pure DNS encoding/decoding
python3 tests/test_dns_server.py       # 27 tests - Server-side logic
python3 tests/test_dns_integration.py  # 11 tests - End-to-end scenarios
```

### Running the C2 System
```bash
# Terminal 1: Start operator shell (DNS server auto-starts via configure-ec2)
make operator                   # Interactive shell for sending commands

# Terminal 2: Monitor CloudWatch logs (optional)
make logs                       # Watch DNS queries and exfiltrated data

# Terminal 3: Execute payload in Code Interpreter (if not using interactive mode)
make sandbox                    # Executes execute_payload.py

# Note: DNS server on EC2 starts automatically via configure-ec2
# Manual SSH access (if needed): aws ssm start-session --target $EC2_INSTANCE_ID
```

### Development Workflow
```bash
# Update DNS server and redeploy
make update-dns                 # Upload to S3 + redeploy to EC2

# Check DNS server status
make check-dns                  # Verify DNS server is running

# View session activity
tail -f attacker_shell.log      # All operator shell activity logged here

# Operator shell variants
make shell-interactive          # Interactive shell (same as make operator)
make shell-interactive-verbose  # Interactive shell with verbose logging
make shell-generate             # Generate payload and display it
make shell-send CMD="whoami" SESSION="sess_abc123"  # Send command to specific session
make shell-receive SESSION="sess_abc123"            # Retrieve output from session

# Kill active session
make kill-session               # Terminate active Code Interpreter session
```

### Cleanup
```bash
make terraform-destroy          # Destroy all AWS resources
```

## Project Structure

```
.
├── src/                        # Core Python modules
│   ├── attacker_shell.py       # Operator interface (local)
│   ├── payload_client.py       # Client payload (runs in sandbox)
│   └── dns_protocol.py         # Pure DNS encoding/decoding functions
├── terraform/                  # Infrastructure as Code
│   ├── c2-server/
│   │   └── dns_server_with_api.py  # DNS C2 server (deployed to EC2)
│   ├── *.tf                    # Terraform configs (EC2, Route53, S3, IAM)
│   └── README.md               # Infrastructure documentation
├── tests/                      # Unit and integration tests
│   ├── test_dns_protocol.py    # Protocol tests (36 tests)
│   ├── test_dns_server.py      # Server tests (27 tests)
│   ├── test_dns_integration.py # Integration tests (11 tests)
│   └── mock_dns_server.py      # Mock server for integration testing
├── scripts/                    # Automation scripts
│   ├── configure_ec2.sh        # Deploy DNS server to EC2
│   └── check_dns_status.sh     # Verify DNS server running
├── helpers/                    # Utility functions
├── Makefile                    # Development commands
└── requirements.txt            # Python dependencies
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
