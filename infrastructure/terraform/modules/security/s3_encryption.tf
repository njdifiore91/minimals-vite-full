# S3 Encryption Configuration
# This file configures server-side encryption for S3 buckets used for document storage,
# supporting both AES-256 and KMS-based encryption options.

# Create a KMS key for S3 encryption if KMS encryption is selected
resource "aws_kms_key" "s3_encryption" {
  count = var.s3_encryption_type == "aws:kms" ? 1 : 0
  
  description             = "KMS key for S3 bucket encryption in ${var.environment} environment"
  
  deletion_window_in_days = 30
  
  enable_key_rotation     = true
  
  policy                  = data.aws_iam_policy_document.s3_kms_key_policy[0].json
  
  tags                    = merge(local.common_tags, {
    Name = "${local.name_prefix}-s3-encryption-key"
  })

}

# Create an alias for the KMS key for easier reference
resource "aws_kms_alias" "s3_encryption" {
  count = var.s3_encryption_type == "aws:kms" ? 1 : 0
  
  name          = "alias/${local.name_prefix}-s3-encryption"
  
  target_key_id = aws_kms_key.s3_encryption[0].key_id

}

# Define the KMS key policy to allow S3 to use the key for encryption/decryption
data "aws_iam_policy_document" "s3_kms_key_policy" {
  count = var.s3_encryption_type == "aws:kms" ? 1 : 0
  
  statement {
    
    sid    = "AllowS3Service"
    
    effect = "Allow"
    
    principals {
      
      type        = "Service"
      
      identifiers = ["s3.amazonaws.com"]
    
    }
    
    actions = [
      
      "kms:Encrypt",
      
      "kms:Decrypt",
      
      "kms:ReEncrypt*",
      
      "kms:GenerateDataKey*",
      
      "kms:DescribeKey"
    
    ]
    
    resources = ["*"]
  
  }
  
  statement {
    
    sid    = "AllowKeyAdministration"
    
    effect = "Allow"
    
    principals {
      
      type        = "AWS"
      
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    
    }
    
    actions = [
      
      "kms:Create*",
      
      "kms:Describe*",
      
      "kms:Enable*",
      
      "kms:List*",
      
      "kms:Put*",
      
      "kms:Update*",
      
      "kms:Revoke*",
      
      "kms:Disable*",
      
      "kms:Get*",
      
      "kms:Delete*",
      
      "kms:TagResource",
      
      "kms:UntagResource",
      
      "kms:ScheduleKeyDeletion",
      
      "kms:CancelKeyDeletion"
    
    ]
    
    resources = ["*"]
  
  }

}

# Get the current AWS account ID
data "aws_caller_identity" "current" {}

# Create an S3 bucket encryption configuration for AES-256 encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "aes256" {
  
  for_each = var.s3_encryption_type == "AES256" ? toset([for name, value in var.s3_bucket_names : value]) : toset([])
  
  bucket   = each.key
  
  rule {
    
    apply_server_side_encryption_by_default {
      
      sse_algorithm = "AES256"
    
    }
    
    bucket_key_enabled = true
  
  }

}

# Create an S3 bucket encryption configuration for KMS encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "kms" {
  
  for_each = var.s3_encryption_type == "aws:kms" ? toset([for name, value in var.s3_bucket_names : value]) : toset([])
  
  bucket   = each.key
  
  rule {
    
    apply_server_side_encryption_by_default {
      
      sse_algorithm     = "aws:kms"
      
      kms_master_key_id = aws_kms_key.s3_encryption[0].arn
    
    }
    
    bucket_key_enabled = true
  
  }

}

# Create a policy document for S3 bucket encryption
data "aws_iam_policy_document" "s3_encryption_policy" {
  
  statement {
    
    sid    = "DenyUnencryptedObjectUploads"
    
    effect = "Deny"
    
    principals {
      
      type        = "*"
      
      identifiers = ["*"]
    
    }
    
    actions = ["s3:PutObject"]
    
    resources = [
      
      for name, value in var.s3_bucket_names : "arn:aws:s3:::${value}/*"
    
    ]
    
    condition {
      
      test     = "StringNotEquals"
      
      variable = "s3:x-amz-server-side-encryption"
      
      values   = [var.s3_encryption_type]
    
    }
  
  }
  
  statement {
    
    sid    = "DenyInsecureConnections"
    
    effect = "Deny"
    
    principals {
      
      type        = "*"
      
      identifiers = ["*"]
    
    }
    
    actions = ["s3:*"]
    
    resources = [
      
      for name, value in var.s3_bucket_names : "arn:aws:s3:::${value}/*"
    
    ]
    
    condition {
      
      test     = "Bool"
      
      variable = "aws:SecureTransport"
      
      values   = ["false"]
    
    }
  
  }

}

# Apply the bucket policy to enforce encryption
resource "aws_s3_bucket_policy" "encryption_policy" {
  
  for_each = toset([for name, value in var.s3_bucket_names : value])
  
  bucket   = each.key
  
  policy   = data.aws_iam_policy_document.s3_encryption_policy.json
  
  depends_on = [
    
    aws_s3_bucket_server_side_encryption_configuration.aes256,
    
    aws_s3_bucket_server_side_encryption_configuration.kms
  
  ]

}

# Create an IAM policy for accessing the KMS key
resource "aws_iam_policy" "s3_kms_access" {
  
  count       = var.s3_encryption_type == "aws:kms" ? 1 : 0
  
  name        = "${local.name_prefix}-s3-kms-access"
  
  description = "Policy for accessing the S3 KMS encryption key"
  
  policy      = data.aws_iam_policy_document.s3_kms_access[0].json

}

# Define the IAM policy document for accessing the KMS key
data "aws_iam_policy_document" "s3_kms_access" {
  
  count = var.s3_encryption_type == "aws:kms" ? 1 : 0
  
  statement {
    
    sid    = "AllowKeyUsage"
    
    effect = "Allow"
    
    actions = [
      
      "kms:Encrypt",
      
      "kms:Decrypt",
      
      "kms:ReEncrypt*",
      
      "kms:GenerateDataKey*",
      
      "kms:DescribeKey"
    
    ]
    
    resources = [aws_kms_key.s3_encryption[0].arn]
  
  }

}

# Create a default encryption configuration for new buckets
resource "aws_s3_account_public_access_block" "default" {
  
  block_public_acls       = true
  
  block_public_policy     = true
  
  ignore_public_acls      = true
  
  restrict_public_buckets = true

}

# Add outputs for the encryption configuration
output "s3_encryption_type" {
  
  description = "Type of encryption used for S3 buckets"
  
  value       = var.s3_encryption_type

}

output "s3_kms_key_arn" {
  
  description = "ARN of the KMS key used for S3 encryption"
  
  value       = var.s3_encryption_type == "aws:kms" ? aws_kms_key.s3_encryption[0].arn : null

}

output "s3_kms_key_id" {
  
  description = "ID of the KMS key used for S3 encryption"
  
  value       = var.s3_encryption_type == "aws:kms" ? aws_kms_key.s3_encryption[0].key_id : null

}

output "s3_kms_access_policy_arn" {
  
  description = "ARN of the IAM policy for accessing the S3 KMS key"
  
  value       = var.s3_encryption_type == "aws:kms" ? aws_iam_policy.s3_kms_access[0].arn : null

}