# Data source to lookup existing Route53 hosted zone
# Supports lookup by domain name or hosted zone ID
# Hack because in our test account we have 2 with the same name. Sorry for the mess
data "aws_route53_zone" "main" {
  name    = var.domain_name != "" ? var.domain_name : null
  zone_id = var.domain_name == "" ? var.hosted_zone_id : null
}

locals {
  domain_name = data.aws_route53_zone.main.name
}

# A record for ns1.domain pointing to EC2 instance
resource "aws_route53_record" "ns1" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "ns1.${local.domain_name}"
  type    = "A"
  ttl     = 60
  records = [aws_instance.dns_shell.public_ip]
}

# NS record for c2.domain delegation
resource "aws_route53_record" "c2_ns" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "c2.${local.domain_name}"
  type    = "NS"
  ttl     = 60
  records = ["ns1.${local.domain_name}"]
}

# Note: Do NOT create an A record for c2.domain as it conflicts with NS delegation
# The NS record delegates all queries for c2.domain and *.c2.domain to ns1.domain
