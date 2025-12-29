# Data sources

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_region" "current" {}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}
