output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.dns_shell.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.dns_shell.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.dns_shell.private_ip
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.dns_shell.id
}

output "iam_role_name" {
  description = "Name of the IAM role"
  value       = aws_iam_role.dns_shell.name
}

output "iam_role_arn" {
  description = "ARN of the IAM role"
  value       = aws_iam_role.dns_shell.arn
}

output "hosted_zone_id" {
  description = "Route53 hosted zone ID"
  value       = data.aws_route53_zone.main.zone_id
}

output "hosted_zone_name_servers" {
  description = "Route53 hosted zone name servers"
  value       = data.aws_route53_zone.main.name_servers
}

output "ns1_fqdn" {
  description = "FQDN of the ns1 DNS record"
  value       = aws_route53_record.ns1.fqdn
}

output "c2_fqdn" {
  description = "FQDN of the c2 DNS record"
  value       = aws_route53_record.c2_ns.fqdn
}

output "bedrock_code_interpreter_id" {
  description = "ID of the Bedrock AgentCore Code Interpreter"
  value       = aws_bedrockagentcore_code_interpreter.main.code_interpreter_id
}

output "bedrock_code_interpreter_arn" {
  description = "ARN of the Bedrock AgentCore Code Interpreter"
  value       = aws_bedrockagentcore_code_interpreter.main.code_interpreter_arn
}

output "bedrock_execution_role_arn" {
  description = "ARN of the Bedrock Code Interpreter execution role (realistic misconfiguration)"
  value       = aws_iam_role.bedrock_code_interpreter.arn
}

output "bedrock_role_policies" {
  description = "IAM policies attached to Code Interpreter role"
  value = [
    "AmazonS3ReadOnlyAccess",
    "AmazonDynamoDBFullAccess"
  ]
}

output "s3_sensitive_bucket" {
  description = "S3 bucket with sensitive demo data"
  value       = aws_s3_bucket.sensitive_demo.id
}

output "dynamodb_customer_table" {
  description = "DynamoDB table with customer records"
  value       = aws_dynamodb_table.sensitive_customer_data.name
}

output "dynamodb_transaction_table" {
  description = "DynamoDB table with payment transactions"
  value       = aws_dynamodb_table.payment_transactions.name
}

output "s3_bucket" {
  description = "S3 bucket name for artifacts"
  value       = aws_s3_bucket.agentcore_hacking.id
}

output "s3_artifacts_uploaded" {
  description = "List of artifacts uploaded to S3 for EC2 deployment"
  value = {
    dns_server = "s3://${aws_s3_bucket.agentcore_hacking.id}/${aws_s3_object.dns_server_with_api.key}"
  }
}

