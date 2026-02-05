# Attacker Infrastructure

DNS C2 server and attack tools for the DNS exfiltration security demo.

## Quick Start

```bash
# 1. Set up AWS profile
cp .env.example .env
# Edit .env to set AWS_PROFILE

# 2. Install dependencies with uv
make setup

# 3. Deploy C2 infrastructure
make deploy

# 4. Start operator shell
make operator
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python dependency management
- AWS CLI configured
- Terraform

## Commands

### Deployment

| Command | Description |
|---------|-------------|
| `make setup` | Install dependencies with uv |
| `make terraform-init` | Initialize Terraform |
| `make terraform-plan` | Preview changes |
| `make terraform-apply` | Apply changes (with confirmation) |
| `make deploy` | Init + plan + apply + configure EC2 |
| `make configure-ec2` | Deploy DNS server to EC2 |
| `make env-from-terraform` | Generate .env from Terraform outputs |

### Attack Operations

| Command | Description |
|---------|-------------|
| `make operator` | Start interactive C2 shell |
| `make generate-csv` | Generate malicious CSV payload |
| `make attack TARGET=<url>` | Send attack to victim chatbot |

### Monitoring

| Command | Description |
|---------|-------------|
| `make logs` | Tail DNS C2 server CloudWatch logs |
| `make check-dns` | Check if DNS server is running |

### Testing

| Command | Description |
|---------|-------------|
| `make test` | Run all tests |

### Cleanup

| Command | Description |
|---------|-------------|
| `make clean` | Remove .venv and build artifacts |
| `make terraform-destroy` | Destroy infrastructure |
| `make destroy` | Destroy infrastructure and clean |

## Using the CLI Directly

```bash
uv run c2 --help              # Show all commands
uv run c2 generate-csv        # Generate malicious CSV
uv run c2 attack <url>        # Attack a target
uv run c2 send "cmd" -s <id>  # Send command to session
uv run c2 receive -s <id>     # Receive output from session
uv run c2 status              # Check C2 server status
```

## Architecture

- **EC2**: DNS C2 server (port 53 + port 8080 API)
- **Route53**: DNS delegation for c2.domain.com
- **S3**: Stores DNS server script

## DNS Protocol

Commands flow: Operator -> HTTP API (8080) -> DNS Server -> DNS Queries -> Payload

Data exfiltration: Payload -> DNS Queries -> DNS Server -> CloudWatch Logs
