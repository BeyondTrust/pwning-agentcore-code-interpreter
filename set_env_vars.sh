#!/bin/bash
# Export Terraform outputs as environment variables
# Usage: source set_env_vars.sh

echo "✓ Exporting Terraform environment variables..."

pushd terraform > /dev/null

export EC2_INSTANCE_ID=$(terraform output -raw instance_id)
export EC2_IP=$(terraform output -raw instance_public_ip)
export S3_BUCKET=$(terraform output -raw s3_bucket)
export DOMAIN=$(terraform output -raw c2_fqdn)

popd > /dev/null

echo "  EC2_INSTANCE_ID=$EC2_INSTANCE_ID"
echo "  EC2_IP=$EC2_IP"
echo "  S3_BUCKET=$S3_BUCKET"
echo "  DOMAIN=$DOMAIN"
echo "✓ Done. Environment variables set."

