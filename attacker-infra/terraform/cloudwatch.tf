# CloudWatch Log Group for DNS C2 Server
resource "aws_cloudwatch_log_group" "dns_c2_server" {
  name              = "/aws/ec2/dns-c2-server"
  retention_in_days = 7

  tags = var.tags
}

