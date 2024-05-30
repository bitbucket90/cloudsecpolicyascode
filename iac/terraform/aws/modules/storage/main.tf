#------------------------------------------------------------
# Create S3 Bucket 
#------------------------------------------------------------
resource "aws_s3_bucket" "clsec_bucket" {
  bucket = var.bucket_name
  tags = merge(var.tags,{"backup":"standard","data-classification":"${var.data_class}","data-type":"${var.data_type}"})
}

# Enable Bucket Encryption 
resource "aws_s3_bucket_server_side_encryption_configuration" "clsec_bucket_encryption" {
  bucket        = aws_s3_bucket.clsec_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# Bucket Versioning | Supplied as Boolean in var.version_bucket if True then Enabled else Disabled | Default is True  
resource "aws_s3_bucket_versioning" "clsec_bucket_versioning" {
  bucket        = aws_s3_bucket.clsec_bucket.id
  versioning_configuration {
    status = var.version_bucket ? "Enabled" : "Disabled"
  }
}

# Enable Bucket Logging 
resource "aws_s3_bucket_logging" "clsec_bucket_storage" {
  bucket        = aws_s3_bucket.clsec_bucket.id
  target_bucket = aws_s3_bucket.clsec_bucket.id
  target_prefix = "${aws_s3_bucket.clsec_bucket.id}/"
}

# Enable Lifecyle Configuration Rule
resource "aws_s3_bucket_lifecycle_configuration" "clsec_bucket_lifecylce" {
  bucket        = aws_s3_bucket.clsec_bucket.id
  rule {
    id = "archive_objects_rule"
    status = "Enabled"
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
}

# Disable Bucket Public Access
resource "aws_s3_bucket_public_access_block" "block_public_access_replica" {
  bucket = aws_s3_bucket.clsec_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Policy | Restrict to only CG Organization
data "aws_iam_policy_document" "restrict_to_cg_org" {
  statement {
    sid = "DenyOutsideOrg"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      "${aws_s3_bucket.clsec_bucket.arn}/*",
      "${aws_s3_bucket.clsec_bucket.arn}"
    ]
    principals {
      identifiers = ["*"]
      type        = "AWS"
    }
    condition {
      test     = "StringNotLike"
      variable = "aws:PrincipalOrgID"
      values   = ["o-1eax4cor5e"]
    }
  }
} 

# Attach Bucket Policy 
resource "aws_s3_bucket_policy" "restrict_internal_only" {
  bucket = aws_s3_bucket.clsec_bucket.id
  policy = data.aws_iam_policy_document.restrict_to_cg_org.json
}
