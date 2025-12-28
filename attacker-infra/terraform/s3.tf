# S3 bucket for C2 server artifacts
resource "aws_s3_bucket" "c2_artifacts" {
  bucket        = var.s3_bucket_name
  force_destroy = true

  tags = var.tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "c2_artifacts" {
  bucket = aws_s3_bucket.c2_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Upload DNS C2 server to S3
resource "aws_s3_object" "dns_server_with_api" {
  bucket = aws_s3_bucket.c2_artifacts.id
  key    = "dns-server/dns_server_with_api.py"
  source = "${path.module}/c2-server/dns_server_with_api.py"
  etag   = filemd5("${path.module}/c2-server/dns_server_with_api.py")

  tags = var.tags
}
