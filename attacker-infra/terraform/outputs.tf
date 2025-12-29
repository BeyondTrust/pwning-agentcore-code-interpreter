output "instance_id" {
  description = "ID of the EC2 C2 server instance"
  value       = aws_instance.dns_shell.id
}

output "instance_public_ip" {
  description = "Public IP address of the C2 server"
  value       = aws_instance.dns_shell.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the C2 server"
  value       = aws_instance.dns_shell.private_ip
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.dns_shell.id
}

output "iam_role_name" {
  description = "Name of the IAM role"
  value       = aws_iam_role.c2_server.name
}

output "iam_role_arn" {
  description = "ARN of the IAM role"
  value       = aws_iam_role.c2_server.arn
}

output "hosted_zone_id" {
  description = "Route53 hosted zone ID"
  value       = data.aws_route53_zone.main.zone_id
}

output "hosted_zone_name_servers" {
  description = "Route53 hosted zone name servers"
  value       = data.aws_route53_zone.main.name_servers
}

output "ns1_fqdn" {
  description = "FQDN of the ns1 DNS record"
  value       = aws_route53_record.ns1.fqdn
}

output "c2_fqdn" {
  description = "FQDN of the c2 DNS record"
  value       = aws_route53_record.c2_ns.fqdn
}

output "s3_bucket" {
  description = "S3 bucket name for C2 artifacts"
  value       = aws_s3_bucket.c2_artifacts.id
}

output "s3_artifacts_uploaded" {
  description = "List of artifacts uploaded to S3 for EC2 deployment"
  value = {
    dns_server = "s3://${aws_s3_bucket.c2_artifacts.id}/${aws_s3_object.dns_server_with_api.key}"
  }
}
