# Security Group
resource "aws_security_group" "dns_shell" {
  name        = var.security_group_name
  description = "Security group for DNS shell server"
  vpc_id      = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name = var.security_group_name
    }
  )
}

# SSH
resource "aws_security_group_rule" "ssh" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = var.allowed_ingress_cidrs
  description       = "SSH"
  security_group_id = aws_security_group.dns_shell.id
}

# DNS TCP
resource "aws_security_group_rule" "dns_tcp" {
  type              = "ingress"
  from_port         = 53
  to_port           = 53
  protocol          = "tcp"
  cidr_blocks       = var.allowed_ingress_cidrs
  description       = "DNS TCP"
  security_group_id = aws_security_group.dns_shell.id
}

# DNS UDP
resource "aws_security_group_rule" "dns_udp" {
  type              = "ingress"
  from_port         = 53
  to_port           = 53
  protocol          = "udp"
  cidr_blocks       = var.allowed_ingress_cidrs
  description       = "DNS UDP"
  security_group_id = aws_security_group.dns_shell.id
}

# Port 1337
resource "aws_security_group_rule" "port_1337" {
  type              = "ingress"
  from_port         = 1337
  to_port           = 1337
  protocol          = "tcp"
  cidr_blocks       = var.allowed_ingress_cidrs
  description       = "C2 listener"
  security_group_id = aws_security_group.dns_shell.id
}

# Port 8080 - Management interface
resource "aws_security_group_rule" "port_8080" {
  type              = "ingress"
  from_port         = 8080
  to_port           = 8080
  protocol          = "tcp"
  cidr_blocks       = var.allowed_ingress_cidrs
  description       = "DNS Shell Management Interface"
  security_group_id = aws_security_group.dns_shell.id
}

# Egress - allow all outbound traffic
resource "aws_security_group_rule" "egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.dns_shell.id
}
