/**
 * S3 Encryption Module
 * 
 * This module configures server-side encryption for S3 buckets used in the MCA Application
 * Processing System. It supports both AES-256 (SSE-S3) and KMS-based (SSE-KMS) encryption
 * options to ensure all documents stored in S3 are encrypted at rest.
 *
 * Features:
 * - Server-side encryption with S3-managed keys (SSE-S3) enabled by default
 * - Option to use KMS-managed keys (SSE-KMS) for sensitive document categories
 * - Blocks all public access to S3 buckets by default
 * - Configurable bucket key for cost-effective KMS encryption
 * 
 * This module is designed to be used with the following bucket types:
 * - mca-documents-{environment} - General document storage
 * - mca-sensitive-documents-{environment} - Storage for sensitive documents requiring KMS encryption
 */

variable "bucket_name" {
  description = "Name of the S3 bucket to apply encryption configuration"
  type        = string
}

variable "encryption_type" {
  description = "Type of server-side encryption to use (AES256 or aws:kms)"
  type        = string
  default     = "AES256"
  validation {
    condition     = contains(["AES256", "aws:kms"], var.encryption_type)
    error_message = "Encryption type must be either AES256 or aws:kms."
  }
}

variable "kms_key_id" {
  description = "ARN of the KMS key to use for encryption (required when encryption_type is aws:kms)"
  type        = string
  default     = null
}

variable "enable_bucket_key" {
  description = "Whether to use S3 Bucket Keys for SSE-KMS"
  type        = bool
  default     = true
}

variable "tags" {
  description = "A map of tags to assign to the encryption resources"
  type        = map(string)
  default     = {}
}

variable "environment" {
  description = "Deployment environment (e.g., development, staging, production)"
  type        = string
  default     = "development"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

# Local variables for configuration and validation
locals {
  # Determine if KMS encryption is being used
  is_kms_encryption = var.encryption_type == "aws:kms"
  
  # Validate that KMS key ID is provided when KMS encryption is selected
  validate_kms_key  = local.is_kms_encryption && var.kms_key_id == null ? tobool("KMS key ID is required when encryption_type is aws:kms") : true
  
  # Common tags to be applied to all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Service     = "mca-document-storage"
      Encryption  = var.encryption_type
    }
  )
}

# S3 bucket server-side encryption configuration
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = var.bucket_name

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.encryption_type
      kms_master_key_id = local.is_kms_encryption ? var.kms_key_id : null
    }
    
    bucket_key_enabled = local.is_kms_encryption ? var.enable_bucket_key : null
  }
}

# S3 bucket public access block to ensure no public access
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = var.bucket_name

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket policy to enforce encryption in transit
data "aws_iam_policy_document" "require_ssl" {
  statement {
    sid    = "DenyNonSSLRequests"
    effect = "Deny"
    
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    
    actions = [
      "s3:*"
    ]
    
    resources = [
      "arn:aws:s3:::${var.bucket_name}",
      "arn:aws:s3:::${var.bucket_name}/*"
    ]
    
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "require_ssl" {
  bucket = var.bucket_name
  policy = data.aws_iam_policy_document.require_ssl.json
}

# Outputs
output "encryption_configuration" {
  description = "The encryption configuration applied to the S3 bucket"
  value = {
    bucket_name        = var.bucket_name
    encryption_type    = var.encryption_type
    kms_key_id         = local.is_kms_encryption ? var.kms_key_id : "N/A"
    bucket_key_enabled = local.is_kms_encryption ? var.enable_bucket_key : false
    environment        = var.environment
  }
}

output "bucket_name" {
  description = "The name of the S3 bucket with encryption configured"
  value       = var.bucket_name
}

output "encryption_type" {
  description = "The type of encryption applied to the S3 bucket"
  value       = var.encryption_type
}

output "ssl_enforced" {
  description = "Indicates that SSL/TLS is enforced for all bucket operations"
  value       = true
}

# Example usage:
#
# # Standard document bucket with AES-256 encryption
# module "document_bucket_encryption" {
#   source = "../modules/security/s3_encryption"
#
#   bucket_name    = "mca-documents-production"
#   encryption_type = "AES256"  # Default S3-managed encryption
# }
#
# # Sensitive document bucket with KMS encryption
# module "sensitive_document_bucket_encryption" {
#   source = "../modules/security/s3_encryption"
#
#   bucket_name    = "mca-sensitive-documents-production"
#   encryption_type = "aws:kms"
#   kms_key_id     = aws_kms_key.document_encryption.arn
#   enable_bucket_key = true  # Use S3 Bucket Keys for cost-effective KMS encryption
# }
#
# # Usage in different environments
# module "document_bucket_encryption_staging" {
#   source = "../modules/security/s3_encryption"
#
#   bucket_name    = "mca-documents-staging"
#   encryption_type = "AES256"
# }