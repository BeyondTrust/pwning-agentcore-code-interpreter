variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Using a prefix rather than name as bucket names must be globally unique
variable "s3_c2_bucket_prefix" {
  description = "Prefix for the S3 bucket name for S3 C2 channel sessions"
  type        = string
  default     = "agentcore-c2-sessions-"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}