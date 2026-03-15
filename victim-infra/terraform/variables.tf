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

variable "model_id" {
  description = "Bedrock model ID for the chatbot LLM"
  type        = string
  default     = "us.meta.llama4-scout-17b-instruct-v1:0"
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

variable "allowed_ingress_cidrs" {
  description = "List of CIDR blocks allowed for ingress (HTTP, HTTPS)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
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
