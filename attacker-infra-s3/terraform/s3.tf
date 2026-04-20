# S3 bucket for C2 channel sessions (presigned URL-based)
resource "aws_s3_bucket" "c2_session_bucket" {
  bucket_prefix = var.s3_c2_bucket_prefix
  force_destroy = true

  tags = var.tags
}

resource "aws_s3_bucket_public_access_block" "c2_sessions" {
  bucket = aws_s3_bucket.c2_session_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "c2_sessions" {
  bucket = aws_s3_bucket.c2_session_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}