output "s3_c2_bucket" {
  description = "S3 bucket name for S3 C2 channel"
  value       = aws_s3_bucket.c2_session_bucket.id
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}