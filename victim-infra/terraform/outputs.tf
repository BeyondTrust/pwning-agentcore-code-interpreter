# Outputs for Victim Infrastructure

output "chatbot_url" {
  description = "Public URL of the victim chatbot (use this for the attack)"
  value       = "http://${aws_lb.chatbot.dns_name}"
}

output "chatbot_alb_dns" {
  description = "ALB DNS name"
  value       = aws_lb.chatbot.dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing chatbot image"
  value       = aws_ecr_repository.chatbot.repository_url
}

output "code_interpreter_id" {
  description = "Code Interpreter ID"
  value       = aws_bedrockagentcore_code_interpreter.main.id
}

output "code_interpreter_arn" {
  description = "Code Interpreter ARN"
  value       = aws_bedrockagentcore_code_interpreter.main.arn
}

output "sensitive_bucket" {
  description = "S3 bucket containing sensitive demo data"
  value       = aws_s3_bucket.sensitive.id
}

output "customers_table" {
  description = "DynamoDB table with customer data"
  value       = aws_dynamodb_table.customers.name
}

output "database_secret_arn" {
  description = "Secrets Manager ARN for database credentials"
  value       = aws_secretsmanager_secret.database.arn
}

output "api_tokens_secret_arn" {
  description = "Secrets Manager ARN for API tokens"
  value       = aws_secretsmanager_secret.api_tokens.arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.chatbot.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.chatbot.name
}

# Output for easy copy-paste attack command
output "attack_command" {
  description = "Command to run the attack (use with attacker-infra)"
  value       = "make attack TARGET=http://${aws_lb.chatbot.dns_name}"
}
