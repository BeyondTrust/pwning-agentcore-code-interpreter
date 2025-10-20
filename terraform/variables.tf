variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "ssh_allowed_cidrs" {
  description = "List of CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "instance_name" {
  description = "Name tag for the EC2 instance"
  type        = string
  default     = "dns-shell-sandbox-dns-shell-server"
}

variable "security_group_name" {
  description = "Name of the security group"
  type        = string
  default     = "dns-shell-sandbox-dns-shell-sg"
}

variable "iam_role_name" {
  description = "Name of the IAM role"
  type        = string
  default     = "dns-shell-sandbox-dns-shell-role"
}

variable "key_name" {
  description = "EC2 key pair name (optional, SSM is configured)"
  type        = string
  default     = null
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for agentcore hacking"
  type        = string
  default     = "agentcore-hacking"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "domain_name" {
  description = "Domain name for Route53 hosted zone"
  type        = string
  default     = "bt-research-control.com"
}

