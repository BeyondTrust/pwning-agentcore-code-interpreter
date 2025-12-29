# IAM Role for EC2 C2 server
resource "aws_iam_role" "c2_server" {
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
  role       = aws_iam_role.c2_server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Inline policy for CloudWatch Logs
resource "aws_iam_role_policy" "c2_server_logs" {
  name = "${var.iam_role_name}-logs-policy"
  role = aws_iam_role.c2_server.id

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
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/dns-c2-server${var.resource_suffix}:*"
        ]
      }
    ]
  })
}

# Inline policy for S3 access (C2 artifacts bucket only)
resource "aws_iam_role_policy" "s3_access" {
  name = "${var.iam_role_name}-s3-policy"
  role = aws_iam_role.c2_server.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      }
    ]
  })
}

# IAM instance profile
resource "aws_iam_instance_profile" "c2_server" {
  name = "${var.iam_role_name}-profile"
  role = aws_iam_role.c2_server.name

  tags = var.tags
}
