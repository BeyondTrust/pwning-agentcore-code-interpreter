variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "victim-chatbot"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.1.0.0/16"
}

variable "container_cpu" {
  description = "CPU units for ECS task"
  type        = number
  default     = 256
}

variable "container_memory" {
  description = "Memory (MB) for ECS task"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Project     = "agentcore-security-demo"
    Environment = "demo"
    Purpose     = "security-research"
  }
}
