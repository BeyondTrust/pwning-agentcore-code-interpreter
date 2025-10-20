# IAM Role for EC2 instance
resource "aws_iam_role" "dns_shell" {
  name = var.iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

# Attach AWS managed policy for SSM
resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.dns_shell.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Inline policy for CloudWatch Logs
resource "aws_iam_role_policy" "dns_shell_logs" {
  name = "dns-shell-sandbox-dns-shell-logs-policy"
  role = aws_iam_role.dns_shell.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/dns-shell/*",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/dns-shell/*:*",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/dns-c2-server:*"
        ]
      }
    ]
  })
}

# Inline policy for S3 access
resource "aws_iam_role_policy" "s3_access" {
  name = "s3-access-agentcore-hacking"
  role = aws_iam_role.dns_shell.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "VisualEditor0"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}/*"
      }
    ]
  })
}

# IAM role for Bedrock Code Interpreter
# Demonstrates realistic opportunities for misconfiguration.
# Agentcore Gateway roles can also be applied to Bedrock Code Interpreter because both use the same service principal - bedrock-agentcore.amazonaws.com.
# The bedrock-agentcore-starter-toolkit (published by AWS) provides example IAM roles that have excessive permissions to S3 and DynamoDB. If those were applied to Code Interpreter and code interpreter was used by a vulnerable chatbot, it could lead to data exfiltration.
# Reference: https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/8b8afb5a579524df56ba94ea93e3f286a828b716/src/bedrock_agentcore_starter_toolkit/operations/gateway/constants.py#L84
resource "aws_iam_role" "bedrock_code_interpreter" {
  name = "BedrockCodeInterpreterDemoRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock-agentcore.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name    = "Bedrock Code Interpreter Demo Role"
    Purpose = "VDP - Gateway role mistakenly applied to Code Interpreter"
  })
}

# AmazonS3ReadOnlyAccess - Legitimate for Code Interpreter data analysis
resource "aws_iam_role_policy_attachment" "s3_readonly" {
  role       = aws_iam_role.bedrock_code_interpreter.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# AmazonDynamoDBFullAccess - Common in Gateway roles, accidentally applied to Code Interpreter
resource "aws_iam_role_policy_attachment" "dynamodb_full" {
  role       = aws_iam_role.bedrock_code_interpreter.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

# IAM instance profile
resource "aws_iam_instance_profile" "dns_shell" {
  name = "dns-shell-sandbox-dns-shell-profile"
  role = aws_iam_role.dns_shell.name

  tags = var.tags
}

