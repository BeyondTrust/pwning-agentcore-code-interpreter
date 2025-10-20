# EC2 Instance
resource "aws_instance" "dns_shell" {
  ami                    = "ami-0e2c86481225d3c51"
  instance_type          = "t3.micro"
  key_name               = var.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.dns_shell.id]
  iam_instance_profile   = aws_iam_instance_profile.dns_shell.name

  root_block_device {
    volume_size           = 8
    volume_type           = "gp2"
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "optional"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  tags = merge(
    var.tags,
    {
      Name = var.instance_name
    }
  )

  lifecycle {
    ignore_changes = [
      user_data,
      user_data_base64,
      root_block_device[0].tags,
      root_block_device[0].tags_all
    ]
  }
}

