# IAM Roles and Policies for Victim Chatbot
# NOTE: These are INTENTIONALLY over-permissioned to demonstrate realistic misconfigurations

# =============================================================================
# ECS Task Execution Role (for pulling images, writing logs)
# =============================================================================

resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# =============================================================================
# ECS Task Role (for application access to AWS services)
# =============================================================================

resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

# Allow ECS task to invoke Bedrock AgentCore
resource "aws_iam_role_policy" "ecs_task_bedrock" {
  name = "${var.project_name}-ecs-bedrock-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock-agent-runtime:*",
          "bedrock-agentcore:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# =============================================================================
# Code Interpreter Role - INTENTIONALLY OVER-PERMISSIONED
# This demonstrates a realistic misconfiguration where developers grant
# broad access "to make things work" without following least privilege
# =============================================================================

resource "aws_iam_role" "code_interpreter" {
  name = "${var.project_name}-code-interpreter-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "bedrock.amazonaws.com"
      }
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })

  tags = merge(var.tags, {
    Warning = "INTENTIONALLY-OVERPERMISSIONED-FOR-DEMO"
  })
}

# VULNERABILITY: Full S3 read access - can read ANY bucket in the account
resource "aws_iam_role_policy_attachment" "code_interpreter_s3" {
  role       = aws_iam_role.code_interpreter.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# VULNERABILITY: Full DynamoDB access - can read/write ANY table
resource "aws_iam_role_policy_attachment" "code_interpreter_dynamodb" {
  role       = aws_iam_role.code_interpreter.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

# VULNERABILITY: Secrets Manager read access - can read ANY secret
resource "aws_iam_role_policy_attachment" "code_interpreter_secrets" {
  role       = aws_iam_role.code_interpreter.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

# VULNERABILITY: Additional permissions that are "commonly" granted
resource "aws_iam_role_policy" "code_interpreter_extra" {
  name = "${var.project_name}-code-interpreter-extra"
  role = aws_iam_role.code_interpreter.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSTS"
        Effect = "Allow"
        Action = [
          "sts:GetCallerIdentity",
          "sts:GetAccessKeyInfo"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowEC2Describe"
        Effect = "Allow"
        Action = [
          "ec2:Describe*"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowCloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}
