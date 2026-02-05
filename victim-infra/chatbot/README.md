# Victim Chatbot Application

This is a **deliberately vulnerable** FastAPI application that demonstrates a realistic AI-powered chatbot. It is designed for security research to show how prompt injection attacks can lead to data exfiltration.

## Vulnerability

The application passes user-controlled input (CSV content and messages) directly to AWS Bedrock AgentCore Code Interpreter without sanitization. This allows prompt injection attacks where malicious content embedded in CSV files can trigger arbitrary code execution.

**Attack Vector:**
1. Attacker embeds prompt injection payload in a CSV cell
2. Victim uploads the CSV to this chatbot for "analysis"
3. The unsanitized CSV content is passed to Code Interpreter
4. Prompt injection triggers execution of attacker's payload
5. Payload exfiltrates sensitive data via DNS (sandbox bypass)

## Local Development

**Prerequisites:** Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python dependency management.

```bash
# Install dependencies
uv sync

# Run locally
uv run uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
# Build
docker build -t victim-chatbot .

# Run
docker run -p 8000:8000 \
  -e CODE_INTERPRETER_ID=your-interpreter-id \
  -e AWS_REGION=us-east-1 \
  victim-chatbot
```

## Endpoints

- `GET /` - Web UI for uploading CSV and asking questions
- `GET /health` - Health check endpoint
- `POST /chat/` - General chat endpoint
- `POST /analyze/csv` - **VULNERABLE** - CSV analysis endpoint

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CODE_INTERPRETER_ID` | AWS Bedrock AgentCore Code Interpreter ID | Yes |
| `CODE_INTERPRETER_ARN` | Code Interpreter ARN | No |
| `AWS_REGION` | AWS region | No (default: us-east-1) |
| `SENSITIVE_BUCKET` | S3 bucket with demo data | No |
| `CUSTOMERS_TABLE` | DynamoDB table name | No |

## Security Notice

This application is **intentionally vulnerable** for security research purposes. Do not deploy this in production or with real sensitive data.
