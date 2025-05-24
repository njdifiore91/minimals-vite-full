# KMS keys for encryption in the MCA Application Processing System
# This file defines the KMS keys used for PII field-level encryption and S3 bucket encryption

# ---------------------------------------------------------------------------------------------------------------------
# PII Field-Level Encryption Key
# Used by the Data Service for encrypting Personally Identifiable Information (PII) at the field level in PostgreSQL
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_kms_key" "pii_encryption" {
  description             = "KMS key for PII field-level encryption in the MCA Application Processing System"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  # Key policy allowing the necessary permissions for PII encryption/decryption
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "EnableIAMUserPermissions",
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*",
        Resource = "*"
      },
      {
        Sid    = "AllowDataServiceAccess",
        Effect = "Allow",
        Principal = {
          AWS = var.data_service_role_arn
        },
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        Resource = "*"
      }
    ]
  })

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-pii-encryption-key"
      Service     = "data-service"
      Encryption  = "PII"
    }
  )
}

# Alias for the PII encryption key for easier reference
resource "aws_kms_alias" "pii_encryption" {
  name          = "alias/${var.environment}-pii-encryption"
  target_key_id = aws_kms_key.pii_encryption.key_id
}

# ---------------------------------------------------------------------------------------------------------------------
# S3 Bucket Encryption Key
# Used for server-side encryption of documents and data stored in S3 buckets (SSE-KMS)
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_kms_key" "s3_encryption" {
  description             = "KMS key for S3 bucket encryption in the MCA Application Processing System"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  # Key policy allowing S3 service to use the key for encryption/decryption
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "EnableIAMUserPermissions",
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*",
        Resource = "*"
      },
      {
        Sid    = "AllowS3ServiceAccess",
        Effect = "Allow",
        Principal = {
          Service = "s3.amazonaws.com"
        },
        Action = [
          "kms:GenerateDataKey*",
          "kms:Decrypt"
        ],
        Resource = "*"
      },
      {
        Sid    = "AllowDocumentServiceAccess",
        Effect = "Allow",
        Principal = {
          AWS = var.document_service_role_arn
        },
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        Resource = "*"
      },
      {
        Sid    = "AllowOCRServiceAccess",
        Effect = "Allow",
        Principal = {
          AWS = var.ocr_service_role_arn
        },
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        Resource = "*"
      }
    ]
  })

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-s3-encryption-key"
      Service     = "document-storage"
      Encryption  = "S3"
    }
  )
}

# Alias for the S3 encryption key for easier reference
resource "aws_kms_alias" "s3_encryption" {
  name          = "alias/${var.environment}-s3-encryption"
  target_key_id = aws_kms_key.s3_encryption.key_id
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------------------------------------------------
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "common_tags" {
  description = "Common tags to be applied to all resources"
  type        = map(string)
  default     = {}
}

variable "data_service_role_arn" {
  description = "ARN of the IAM role used by the Data Service"
  type        = string
}

variable "document_service_role_arn" {
  description = "ARN of the IAM role used by the Document Service"
  type        = string
}

variable "ocr_service_role_arn" {
  description = "ARN of the IAM role used by the OCR Service"
  type        = string
}

# ---------------------------------------------------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------------------------------------------------
output "pii_encryption_key_id" {
  description = "ID of the KMS key used for PII field-level encryption"
  value       = aws_kms_key.pii_encryption.key_id
}

output "pii_encryption_key_arn" {
  description = "ARN of the KMS key used for PII field-level encryption"
  value       = aws_kms_key.pii_encryption.arn
}

output "s3_encryption_key_id" {
  description = "ID of the KMS key used for S3 bucket encryption"
  value       = aws_kms_key.s3_encryption.key_id
}

output "s3_encryption_key_arn" {
  description = "ARN of the KMS key used for S3 bucket encryption"
  value       = aws_kms_key.s3_encryption.arn
}