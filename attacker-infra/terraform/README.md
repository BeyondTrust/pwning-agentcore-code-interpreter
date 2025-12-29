# Terraform Infrastructure

This directory contains Terraform configuration to manage the DNS shell sandbox infrastructure in AWS.

## Resources Managed

### IAM Resources
- **IAM Role** (`dns-shell-sandbox-dns-shell-role`)
  - Assume role policy for EC2
  - Attached managed policy: `AmazonSSMManagedInstanceCore`
  - Inline policy: `dns-shell-sandbox-dns-shell-logs-policy` (CloudWatch Logs access)
  - Inline policy: `s3-access-agentcore-hacking` (S3 bucket access)

- **IAM Instance Profile** (`dns-shell-sandbox-dns-shell-profile`)
  - Links the IAM role to EC2 instance

### Network Resources
- **VPC** (`dns-shell-sandbox-vpc`)
  - CIDR: 10.0.0.0/16
  - DNS hostnames and support enabled
- **Internet Gateway** (`dns-shell-sandbox-igw`)
  - Provides internet access for public subnet
- **Public Subnet** (`dns-shell-sandbox-public-subnet`)
  - CIDR: 10.0.1.0/24
  - Availability Zone: us-east-1a
  - Auto-assigns public IPs
- **Route Table** (`dns-shell-sandbox-public-rt`)
  - Routes 0.0.0.0/0 to Internet Gateway
- **Security Group** (`dns-shell-sandbox-dns-shell-sg`)
  - DNS TCP/UDP (port 53) - open to 0.0.0.0/0
  - SSH (port 22) - configurable via `ssh_allowed_cidrs` variable
  - Management API (port 8080) - open to 0.0.0.0/0
  - Port 1337 - open to 0.0.0.0/0
  - All outbound traffic allowed

### Compute Resources
- **EC2 Instance** (`i-03276574a93670cb2`)
  - Name: `dns-shell-sandbox-dns-shell-server`
  - Instance type: t3.micro
  - AMI: ami-0e2c86481225d3c51
  - Key pair: dns-shell-sandbox-key
  - Root volume: 8GB gp2

### DNS Resources
- **Route53 Hosted Zone** (`bt-research-control.com`)
  - Manages DNS for the domain
- **DNS Records**:
  - `ns1.bt-research-control.com` (A) → EC2 instance public IP
  - `c2.bt-research-control.com` (A) → EC2 instance public IP
  - `c2.bt-research-control.com` (NS) → ns1.bt-research-control.com (delegation)
  - `shell.bt-research-control.com` (A) → 54.242.138.37

### Storage Resources
- **S3 Bucket** (`agentcore-hacking`)
  - Versioning enabled
  - Server-side encryption (AES256)

### AI/ML Resources
- **Bedrock AgentCore Code Interpreter** (`dns-shell-code-interpreter`)
  - Network mode: SANDBOX
  - Custom execution role with S3 access to hacking bucket
  - Enables AI agents to execute Python code securely

## Configuration

### Variables

Key variables you can customize (see `variables.tf` for full list):

- `aws_region` - AWS region (default: us-east-1)
- `ssh_allowed_cidrs` - List of CIDR blocks allowed SSH access
- `key_name` - EC2 key pair name (optional, default: null - SSM is configured)
- `instance_name` - Name tag for EC2 instance
- `security_group_name` - Name of the security group
- `iam_role_name` - Name of the IAM role
- `s3_bucket_name` - Name of the S3 bucket (default: agentcore-hacking)
- `domain_name` - Domain name for Route53 hosted zone (default: bt-research-control.com)

### SSH Access Configuration

SSH access is controlled via the `ssh_allowed_cidrs` variable in `terraform.tfvars`. This file is gitignored to keep IP addresses private.

1. Copy the example file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` to specify allowed CIDR blocks and key name:
   ```hcl
   ssh_allowed_cidrs = [
     "203.0.113.0/24",
     "198.51.100.0/24"
   ]
   
   # Optional: specify key pair name (SSM is configured as default access method)
   key_name = "my-key-pair"
   ```

## Usage

### Initialize Terraform
```bash
terraform init
```

### Plan Changes
```bash
terraform plan
```

### Apply Changes
```bash
terraform apply
```

### Destroy Infrastructure
```bash
terraform destroy
```

## Import Existing Resources

All resources have been imported from existing infrastructure. If you need to import them again:

```bash
# IAM resources
terraform import aws_iam_role.dns_shell dns-shell-sandbox-dns-shell-role
terraform import aws_iam_role_policy_attachment.ssm_managed_instance_core dns-shell-sandbox-dns-shell-role/arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
terraform import aws_iam_role_policy.dns_shell_logs dns-shell-sandbox-dns-shell-role:dns-shell-sandbox-dns-shell-logs-policy
terraform import aws_iam_role_policy.s3_access dns-shell-sandbox-dns-shell-role:s3-access-agentcore-hacking
terraform import aws_iam_instance_profile.dns_shell dns-shell-sandbox-dns-shell-profile

# VPC and networking
terraform import aws_vpc.main vpc-0bbbaf4def577a022
terraform import aws_internet_gateway.main igw-0aeff1fa8301acd88
terraform import aws_subnet.public subnet-015c6bcb029f5bd4a
terraform import aws_route_table.public rtb-0e4cb828b8e57ce13
terraform import aws_route_table_association.public subnet-015c6bcb029f5bd4a/rtb-0e4cb828b8e57ce13

# Security group and rules
terraform import aws_security_group.dns_shell sg-03761f2040cbe3dbc
terraform import 'aws_security_group_rule.ssh[0]' sg-03761f2040cbe3dbc_ingress_tcp_22_22_1.0.0.0/8
# ... (other SSH rules)
terraform import aws_security_group_rule.dns_tcp sg-03761f2040cbe3dbc_ingress_tcp_53_53_0.0.0.0/0
terraform import aws_security_group_rule.dns_udp sg-03761f2040cbe3dbc_ingress_udp_53_53_0.0.0.0/0
terraform import aws_security_group_rule.port_1337 sg-03761f2040cbe3dbc_ingress_tcp_1337_1337_0.0.0.0/0
terraform import aws_security_group_rule.port_8080 sg-03761f2040cbe3dbc_ingress_tcp_8080_8080_0.0.0.0/0
terraform import aws_security_group_rule.egress sg-03761f2040cbe3dbc_egress_all_0_0_0.0.0.0/0

# EC2 instance
terraform import aws_instance.dns_shell i-03276574a93670cb2

# Route53 hosted zone and records
terraform import aws_route53_zone.main Z047260910N4L52Y07URX
terraform import aws_route53_record.ns1 Z047260910N4L52Y07URX_ns1.bt-research-control.com._A
terraform import aws_route53_record.c2_ns Z047260910N4L52Y07URX_c2.bt-research-control.com._NS
terraform import aws_route53_record.c2 Z047260910N4L52Y07URX_c2.bt-research-control.com._A
terraform import aws_route53_record.shell Z047260910N4L52Y07URX_shell.bt-research-control.com._A

# S3 bucket
terraform import aws_s3_bucket.agentcore_hacking agentcore-hacking
terraform import aws_s3_bucket_versioning.agentcore_hacking agentcore-hacking
terraform import aws_s3_bucket_server_side_encryption_configuration.agentcore_hacking agentcore-hacking

# Bedrock AgentCore Code Interpreter
terraform import aws_iam_role.bedrock_code_interpreter bedrock-agentcore-code-interpreter-role
terraform import aws_iam_role_policy.bedrock_s3_access bedrock-agentcore-code-interpreter-role:bedrock-s3-access-agentcore-hacking
terraform import aws_bedrockagentcore_code_interpreter.main dns_shell_code_interpreter-15JjdxrOwC
```

## Files

- `terraform.tf` - Terraform configuration (provider, version requirements)
- `data.tf` - Data sources (AWS caller identity)
- `iam.tf` - IAM role, policies, and instance profile
- `network.tf` - VPC, subnets, internet gateway, route tables
- `security_groups.tf` - Security groups and security group rules
- `ec2.tf` - EC2 instance configuration
- `s3.tf` - S3 bucket and related configurations
- `route53.tf` - Route53 hosted zone and DNS records
- `bedrock.tf` - Bedrock AgentCore Code Interpreter and IAM role
- `variables.tf` - Variable definitions
- `outputs.tf` - Output definitions
- `terraform.tfvars` - Variable values (gitignored)
- `terraform.tfvars.example` - Example variable values

## Notes

- The instance's `user_data` is ignored in state management since we imported existing infrastructure
- Root block device tags are also ignored to prevent drift from AWS-managed tags
- All resources are tagged using the `tags` variable from `terraform.tfvars` (gitignored to keep internal tags out of OSS)
- DNS records automatically reference the EC2 instance public IP, so updates to the instance will update DNS
- The Route53 records replace the need for manual `aws route53 change-resource-record-sets` commands
- VPC and networking resources are now fully managed by Terraform, eliminating the need for manual VPC creation
- Security groups are separated from network resources for better organization

