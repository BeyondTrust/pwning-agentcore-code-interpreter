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

# SSH ingress rules - looped for each allowed CIDR
resource "aws_security_group_rule" "ssh" {
  count             = length(var.ssh_allowed_cidrs)
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = [var.ssh_allowed_cidrs[count.index]]
  description       = count.index == 0 && var.ssh_allowed_cidrs[0] == "1.0.0.0/8" ? "SSH broad" : null
  security_group_id = aws_security_group.dns_shell.id
}

# DNS TCP
resource "aws_security_group_rule" "dns_tcp" {
  type              = "ingress"
  from_port         = 53
  to_port           = 53
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "DNS TCP"
  security_group_id = aws_security_group.dns_shell.id
}

# DNS UDP
resource "aws_security_group_rule" "dns_udp" {
  type              = "ingress"
  from_port         = 53
  to_port           = 53
  protocol          = "udp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "DNS UDP"
  security_group_id = aws_security_group.dns_shell.id
}

# Port 1337
resource "aws_security_group_rule" "port_1337" {
  type              = "ingress"
  from_port         = 1337
  to_port           = 1337
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.dns_shell.id
}

# Port 8080 - Management interface
resource "aws_security_group_rule" "port_8080" {
  type              = "ingress"
  from_port         = 8080
  to_port           = 8080
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
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
