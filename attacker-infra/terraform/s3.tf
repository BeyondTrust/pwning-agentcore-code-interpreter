# S3 bucket for agentcore hacking
resource "aws_s3_bucket" "agentcore_hacking" {
  bucket = var.s3_bucket_name

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "agentcore_hacking" {
  bucket = aws_s3_bucket.agentcore_hacking.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "agentcore_hacking" {
  bucket = aws_s3_bucket.agentcore_hacking.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Create a demo "sensitive data" bucket to show IAM role exploitation
resource "aws_s3_bucket" "sensitive_demo" {
  bucket = "${var.s3_bucket_name}-sensitive-data"

  tags = merge(var.tags, {
    Name           = "Demo Sensitive Data Bucket"
    Classification = "Confidential"
    Purpose        = "VDP - Demonstrate IAM Role Access"
  })
}

# Upload a sensitive demo file
resource "aws_s3_object" "sensitive_file_1" {
  bucket  = aws_s3_bucket.sensitive_demo.id
  key     = "financial/Q3-2024-revenue.csv"
  content = <<-EOT
Date,Department,Revenue,Confidential
2024-07-01,Sales,125000,Yes
2024-08-01,Sales,138000,Yes
2024-09-01,Sales,142000,Yes
Total,Sales,405000,CONFIDENTIAL
EOT

  tags = {
    Classification = "Confidential"
    Purpose        = "VDP Demo"
  }
}

resource "aws_s3_object" "sensitive_file_2" {
  bucket  = aws_s3_bucket.sensitive_demo.id
  key     = "credentials/api-keys.json"
  content = <<-EOT
{
  "service": "payment-gateway",
  "api_key": "pk_live_FakeKey",
  "api_secret": "sk_live_FakeSecret",
  "environment": "production",
  "note": "DO NOT SHARE - CONFIDENTIAL"
}
EOT

  tags = {
    Classification = "Secret"
    Purpose        = "VDP Demo"
  }
}

resource "aws_s3_object" "sensitive_file_3" {
  bucket  = aws_s3_bucket.sensitive_demo.id
  key     = "customer-data/users-export.csv"
  content = <<-EOT
user_id,email,name,phone,ssn_last4
1001,john.doe@example.com,John Doe,555-0101,1234
1002,jane.smith@example.com,Jane Smith,555-0102,5678
1003,bob.wilson@example.com,Bob Wilson,555-0103,9012
NOTE: Contains PII - Handle with care
EOT

  tags = {
    Classification = "PII"
    Purpose        = "VDP Demo"
  }
}

# Upload DNS C2 server to S3
resource "aws_s3_object" "dns_server_with_api" {
  bucket = aws_s3_bucket.agentcore_hacking.id
  key    = "dns-server/dns_server_with_api.py"
  source = "${path.module}/c2-server/dns_server_with_api.py"
  etag   = filemd5("${path.module}/c2-server/dns_server_with_api.py")

  tags = var.tags
}

# Note: payload_client.py is NOT uploaded to S3
# It's injected directly from the local filesystem via execute_payload.py
# This simulates a direct code injection attack on a vulnerable chatbot

# Note: operator_shell_remote.py is NOT uploaded to S3
# It runs locally on the attacker's machine, not on EC2
# Only the DNS C2 server needs to be on EC2

