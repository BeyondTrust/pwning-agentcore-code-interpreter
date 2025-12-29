# Victim Infrastructure

Vulnerable chatbot application for the DNS exfiltration security demo.

## Quick Start

```bash
# 1. Set up AWS profile
cp .env.example .env
# Edit .env to set AWS_PROFILE

# 2. Deploy infrastructure
make terraform-yolo

# 3. Build and push container
make docker-push

# 4. Get chatbot URL
make show-url
```

## Commands

### Deployment

| Command | Description |
|---------|-------------|
| `make terraform-init` | Initialize Terraform |
| `make terraform-plan` | Preview changes |
| `make terraform-apply` | Apply changes (with confirmation) |
| `make terraform-yolo` | Init + plan + apply (auto-approve) |
| `make docker-push` | Build and push container to ECR |
| `make deploy` | Full deployment (terraform + docker + ecs) |

### Monitoring

| Command | Description |
|---------|-------------|
| `make show-url` | Show chatbot URL |
| `make ecs-status` | Check ECS service status |
| `make ecs-logs` | Tail ECS container logs |
| `make show-outputs` | Show all Terraform outputs |

### Cleanup

| Command | Description |
|---------|-------------|
| `make terraform-destroy` | Destroy infrastructure |
| `make destroy` | Destroy + clean local files |

## Architecture

- **ECS Fargate**: Runs the FastAPI chatbot container
- **ALB**: Public load balancer (HTTP)
- **Code Interpreter**: Bedrock AgentCore in SANDBOX mode (vulnerable)
- **Sensitive Data**: S3 bucket + DynamoDB with demo PII

## Chatbot Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Web UI |
| `GET /health` | Health check |
| `POST /analyze/csv` | CSV analysis (VULNERABLE to prompt injection) |

## Attack Flow

1. Attacker sends malicious CSV to `/analyze/csv`
2. Chatbot passes CSV to Code Interpreter
3. Prompt injection triggers DNS C2 payload
4. Data exfiltrates via DNS to attacker's C2 server
