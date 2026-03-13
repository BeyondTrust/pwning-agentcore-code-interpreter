# Sensitive Demo Data
# This creates realistic "sensitive" data that will be exfiltrated during the demo
# All data is fake/demo data for security research purposes

# =============================================================================
# S3 Bucket with "Sensitive" Files
# =============================================================================

resource "aws_s3_bucket" "sensitive" {
  bucket = "${var.project_name}-sensitive-${random_id.suffix.hex}"

  tags = merge(var.tags, {
    Name        = "${var.project_name}-sensitive-bucket"
    DataClass   = "DEMO-SENSITIVE"
    Description = "Contains fake sensitive data for security demo"
  })
}

resource "aws_s3_bucket_versioning" "sensitive" {
  bucket = aws_s3_bucket.sensitive.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Customer PII data (FAKE)
resource "aws_s3_object" "customer_records" {
  bucket  = aws_s3_bucket.sensitive.id
  key     = "customers/customer_records.csv"
  content = <<-EOF
customer_id,first_name,last_name,email,ssn,credit_card,phone,address
1001,John,Smith,john.smith@example.com,123-45-6789,4111-1111-1111-1111,555-0101,123 Main St
1002,Jane,Doe,jane.doe@example.com,987-65-4321,5500-0000-0000-0004,555-0102,456 Oak Ave
1003,Robert,Johnson,bob.j@example.com,456-78-9012,3400-0000-0000-009,555-0103,789 Pine Rd
1004,Emily,Williams,emily.w@example.com,321-54-9876,6011-0000-0000-0004,555-0104,321 Elm St
1005,Michael,Brown,m.brown@example.com,654-32-1098,3530-1113-3330-0000,555-0105,654 Maple Dr
EOF

  tags = merge(var.tags, {
    DataType = "PII"
  })
}

# Financial data (FAKE)
resource "aws_s3_object" "financial_report" {
  bucket  = aws_s3_bucket.sensitive.id
  key     = "financial/Q4-2024-revenue.csv"
  content = <<-EOF
quarter,product_line,revenue,profit_margin,customer_count
Q4-2024,Enterprise,12500000,0.42,156
Q4-2024,SMB,8750000,0.35,2341
Q4-2024,Consumer,3200000,0.28,45678
Q4-2024,Government,6800000,0.38,42
TOTAL,ALL,31250000,0.36,48217
EOF

  tags = merge(var.tags, {
    DataType = "Financial"
  })
}

# API credentials (FAKE)
resource "aws_s3_object" "api_keys" {
  bucket  = aws_s3_bucket.sensitive.id
  key     = "credentials/api_keys.json"
  content = jsonencode({
    stripe = {
      api_key      = "sk_live_FAKE_KEY_4eC39HqLyjWDarjtT1zdp7dc"
      webhook_secret = "whsec_FAKE_SECRET_1234567890abcdef"
    }
    sendgrid = {
      api_key = "SG.FAKE_KEY_abcdefghijklmnopqrstuvwxyz"
    }
    twilio = {
      account_sid = "ACFAKE12345678901234567890123456"
      auth_token  = "FAKE_TOKEN_abcdef1234567890"
    }
    aws_partner = {
      access_key = "AKIAFAKEKEY12345678"
      secret_key = "FAKE+SECRET+KEY+1234567890abcdefghij"
    }
  })

  tags = merge(var.tags, {
    DataType = "Credentials"
  })
}

# Internal documentation
resource "aws_s3_object" "internal_docs" {
  bucket  = aws_s3_bucket.sensitive.id
  key     = "internal/security_audit_2024.md"
  content = <<-EOF
# Internal Security Audit Report - Q4 2024
## CONFIDENTIAL - DO NOT DISTRIBUTE

### Executive Summary
This document contains findings from our annual security audit.

### Critical Findings
1. **Database Credentials in Code** - Production DB passwords found in 3 repositories
2. **Unencrypted PII** - Customer SSNs stored without encryption in legacy system
3. **Excessive IAM Permissions** - 47 roles with AdministratorAccess

### Remediation Timeline
- Q1 2025: Rotate all exposed credentials
- Q2 2025: Implement encryption at rest
- Q3 2025: IAM permission audit

### Appendix: Exposed Credentials
- prod-db.internal.company.com: admin / Pr0dP@ssw0rd!2024
- staging-db.internal.company.com: admin / St@g1ngP@ss!
- redis.internal.company.com: default / R3d1sC@che#1
EOF

  tags = merge(var.tags, {
    DataType = "Internal"
  })
}

# =============================================================================
# DynamoDB Table with Customer Data
# =============================================================================

resource "aws_dynamodb_table" "customers" {
  name         = "${var.project_name}-customers-${random_id.suffix.hex}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  tags = merge(var.tags, {
    Name      = "${var.project_name}-customers-table"
    DataClass = "DEMO-PII"
  })
}

# Sample customer records
resource "aws_dynamodb_table_item" "customer_1" {
  table_name = aws_dynamodb_table.customers.name
  hash_key   = aws_dynamodb_table.customers.hash_key

  item = jsonencode({
    customer_id   = { S = "CUST-001" }
    name          = { S = "Alice Johnson" }
    email         = { S = "alice.johnson@example.com" }
    ssn           = { S = "111-22-3333" }
    credit_card   = { S = "4532-1234-5678-9012" }
    account_balance = { N = "15750" }
    status        = { S = "PREMIUM" }
  })
}

resource "aws_dynamodb_table_item" "customer_2" {
  table_name = aws_dynamodb_table.customers.name
  hash_key   = aws_dynamodb_table.customers.hash_key

  item = jsonencode({
    customer_id   = { S = "CUST-002" }
    name          = { S = "Bob Martinez" }
    email         = { S = "bob.martinez@example.com" }
    ssn           = { S = "444-55-6666" }
    credit_card   = { S = "5425-1234-5678-9012" }
    account_balance = { N = "8250" }
    status        = { S = "STANDARD" }
  })
}

resource "aws_dynamodb_table_item" "customer_3" {
  table_name = aws_dynamodb_table.customers.name
  hash_key   = aws_dynamodb_table.customers.hash_key

  item = jsonencode({
    customer_id   = { S = "CUST-003" }
    name          = { S = "Carol White" }
    email         = { S = "carol.white@example.com" }
    ssn           = { S = "777-88-9999" }
    credit_card   = { S = "3782-1234-5678-901" }
    account_balance = { N = "42100" }
    status        = { S = "VIP" }
  })
}

# =============================================================================
# Secrets Manager with Database Credentials
# =============================================================================

resource "aws_secretsmanager_secret" "database" {
  name = "${var.project_name}-database-creds-${random_id.suffix.hex}"

  tags = merge(var.tags, {
    Name      = "${var.project_name}-db-secret"
    DataClass = "DEMO-CREDENTIALS"
  })
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    engine   = "postgresql"
    host     = "prod-database.internal.victim-corp.com"
    port     = 5432
    username = "app_admin"
    password = "Sup3rS3cr3tPr0dP@ssw0rd!"
    database = "customer_data"

    # Additional "leaked" info
    replica_host      = "replica-database.internal.victim-corp.com"
    admin_username    = "postgres_admin"
    admin_password    = "R00tAdm1n#2024!"
    encryption_key    = "aes256-base64-FAKE-KEY-1234567890"
  })
}

resource "aws_secretsmanager_secret" "api_tokens" {
  name = "${var.project_name}-api-tokens-${random_id.suffix.hex}"

  tags = merge(var.tags, {
    Name      = "${var.project_name}-api-secret"
    DataClass = "DEMO-CREDENTIALS"
  })
}

resource "aws_secretsmanager_secret_version" "api_tokens" {
  secret_id = aws_secretsmanager_secret.api_tokens.id
  secret_string = jsonencode({
    github_token       = "ghp_FAKE1234567890abcdefghijklmnopqrstuv"
    slack_bot_token    = "xoxb-FAKE-1234567890-abcdefghijklmnop"
    datadog_api_key    = "FAKE1234567890abcdef1234567890ab"
    pagerduty_token    = "FAKE-PD-TOKEN-1234567890"
    jira_api_token     = "FAKE-JIRA-abcdefghijklmnopqrstuvwxyz"
  })
}
