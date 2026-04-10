# Terraform Infrastructure — S3 C2 Channel

This directory contains Terraform configuration for the S3-based C2 channel.
It is intentionally minimal - just an S3 bucket that
acts as the command-and-control drop point via presigned URLs.

## Resources Managed

### Storage Resources

- **S3 Bucket** (name prefix: `agentcore-c2-sessions-`)
  - Name is auto-generated from the prefix to guarantee global uniqueness
  - `force_destroy = true` so `terraform destroy` empties and removes it cleanly
  - All public access blocked (ACLs, policies, public bucket access)
  - Server-side encryption enabled (AES256)

## Configuration

### Variables

Key variables you can customize (see `variables.tf` for full list):

- `aws_region` - AWS region (default: us-east-1)
- `s3_c2_bucket_prefix` - Prefix for the auto-generated bucket name (default: agentcore-c2-sessions-)
- `tags` - Map of tags to apply to all resources

### Outputs

`s3_c2_bucket`: The actual bucket name (used by `make env-from-terraform`)
`aws_region`: The configured AWS region

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

> `force_destroy = true` is set on the bucket, so Terraform will empty it
> before deleting even if it contains session objects.

## Notes

- The bucket name is non-deterministic (generated from the prefix). Always use
  `make env-from-terraform` after `terraform apply` to update `.env` with the
  real name before running any C2 commands.
- No IAM resources are created here. The attacker's local AWS credentials
  (configured via `AWS_PROFILE` or environment variables) are used directly to
  generate presigned URLs. The credentials never leave the operator machine.
- The bucket does not need to be publicly accessible. Presigned URLs grant
  time-limited access without opening the bucket to the internet.
