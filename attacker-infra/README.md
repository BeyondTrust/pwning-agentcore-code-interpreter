# Attacker Infrastructure

DNS C2 server and attack tools for the DNS exfiltration security demo.

## Quick Start

```bash
# 1. Set up AWS profile
cp .env.example .env
# Edit .env to set AWS_PROFILE

# 2. Install Python dependencies
make install

# 3. Deploy C2 infrastructure
make terraform-yolo

# 4. Start operator shell
make operator
```

## Commands

### Deployment

| Command | Description |
|---------|-------------|
| `make install` | Set up venv and install dependencies |
| `make terraform-init` | Initialize Terraform |
| `make terraform-plan` | Preview changes |
| `make terraform-apply` | Apply changes (with confirmation) |
| `make terraform-yolo` | Init + plan + apply + configure EC2 |
| `make configure-ec2` | Deploy DNS server to EC2 |

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
| `make test-verbose` | Run tests with verbose output |

### Cleanup

| Command | Description |
|---------|-------------|
| `make terraform-destroy` | Destroy infrastructure |

## Architecture

- **EC2**: DNS C2 server (port 53 + port 8080 API)
- **Route53**: DNS delegation for c2.domain.com
- **S3**: Stores DNS server script

## DNS Protocol

Commands flow: Operator → HTTP API (8080) → DNS Server → DNS Queries → Payload

Data exfiltration: Payload → DNS Queries → DNS Server → CloudWatch Logs
