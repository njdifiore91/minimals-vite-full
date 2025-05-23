# IAM Roles and Policies for MCA Application Processing System
# This file defines global IAM resources shared across all environments

# ---------------------------------------------------------------------------------------------------------------------
# PROVIDER CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------
provider "aws" {
  alias = "global"
  region = var.global_region
}

# ---------------------------------------------------------------------------------------------------------------------
# VARIABLES
# ---------------------------------------------------------------------------------------------------------------------
variable "global_region" {
  description = "The AWS region for global resources"
  type        = string
  default     = "us-east-1"
}

variable "environment_account_ids" {
  description = "Map of environment names to AWS account IDs"
  type        = map(string)
  default = {
    development = "111111111111"
    staging     = "222222222222"
    production  = "333333333333"
  }
}

variable "s3_bucket_names" {
  description = "Map of environment names to S3 bucket names"
  type        = map(string)
  default = {
    development = "mca-documents-development"
    staging     = "mca-documents-staging"
    production  = "mca-documents-production"
  }
}

variable "jwt_token_expiry" {
  description = "JWT token expiry time in seconds"
  type        = number
  default     = 3600  # 60 minutes as specified in the technical requirements
}

variable "jwt_algorithm" {
  description = "JWT signing algorithm"
  type        = string
  default     = "RS256"  # As specified in the technical requirements
}

# ---------------------------------------------------------------------------------------------------------------------
# IAM ROLES FOR KUBERNETES SERVICE ACCOUNTS (IRSA)
# ---------------------------------------------------------------------------------------------------------------------

# OIDC Provider for EKS clusters
resource "aws_iam_openid_connect_provider" "eks_oidc_provider" {
  for_each = var.environment_account_ids
  
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["9e99a48a9960b14926bb7f3b02e22da2b0ab7280"] # This should be updated with actual thumbprints
  url             = "https://oidc.eks.${each.key}.amazonaws.com"
}

# ---------------------------------------------------------------------------------------------------------------------
# DOCUMENT SERVICE IAM ROLE
# ---------------------------------------------------------------------------------------------------------------------

# IAM policy for Document Service to access S3 buckets
data "aws_iam_policy_document" "document_service_s3_policy" {
  statement {
    sid    = "AllowDocumentServiceS3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      for bucket_name in values(var.s3_bucket_names) : 
        "arn:aws:s3:::${bucket_name}/*"
    ]
  }
  
  statement {
    sid    = "AllowDocumentServiceS3BucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      for bucket_name in values(var.s3_bucket_names) : 
        "arn:aws:s3:::${bucket_name}"
    ]
  }
}

# IAM role for Document Service
resource "aws_iam_role" "document_service_role" {
  for_each = var.environment_account_ids
  
  name = "document-service-role-${each.key}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks_oidc_provider[each.key].arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks_oidc_provider[each.key].url, "https://", "")}:sub": "system:serviceaccount:document-service:document-service-sa"
          }
        }
      }
    ]
  })
  
  tags = {
    Environment = each.key
    Service     = "document-service"
  }
}

# Attach S3 policy to Document Service role
resource "aws_iam_role_policy" "document_service_s3_policy_attachment" {
  for_each = var.environment_account_ids
  
  name   = "document-service-s3-policy-${each.key}"
  role   = aws_iam_role.document_service_role[each.key].id
  policy = data.aws_iam_policy_document.document_service_s3_policy.json
}

# ---------------------------------------------------------------------------------------------------------------------
# OCR SERVICE IAM ROLE
# ---------------------------------------------------------------------------------------------------------------------

# IAM policy for OCR Service to access S3 buckets
data "aws_iam_policy_document" "ocr_service_s3_policy" {
  statement {
    sid    = "AllowOCRServiceS3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      for bucket_name in values(var.s3_bucket_names) : 
        "arn:aws:s3:::${bucket_name}/*"
    ]
  }
  
  statement {
    sid    = "AllowOCRServiceS3BucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      for bucket_name in values(var.s3_bucket_names) : 
        "arn:aws:s3:::${bucket_name}"
    ]
  }
}

# IAM role for OCR Service
resource "aws_iam_role" "ocr_service_role" {
  for_each = var.environment_account_ids
  
  name = "ocr-service-role-${each.key}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks_oidc_provider[each.key].arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks_oidc_provider[each.key].url, "https://", "")}:sub": "system:serviceaccount:ocr-service:ocr-service-sa"
          }
        }
      }
    ]
  })
  
  tags = {
    Environment = each.key
    Service     = "ocr-service"
  }
}

# Attach S3 policy to OCR Service role
resource "aws_iam_role_policy" "ocr_service_s3_policy_attachment" {
  for_each = var.environment_account_ids
  
  name   = "ocr-service-s3-policy-${each.key}"
  role   = aws_iam_role.ocr_service_role[each.key].id
  policy = data.aws_iam_policy_document.ocr_service_s3_policy.json
}

# ---------------------------------------------------------------------------------------------------------------------
# EMAIL SERVICE IAM ROLE
# ---------------------------------------------------------------------------------------------------------------------

# IAM policy for Email Service to access SES for sending emails
data "aws_iam_policy_document" "email_service_policy" {
  statement {
    sid    = "AllowEmailServiceSESAccess"
    effect = "Allow"
    actions = [
      "ses:SendEmail",
      "ses:SendRawEmail"
    ]
    resources = ["*"]
  }
}

# IAM role for Email Service
resource "aws_iam_role" "email_service_role" {
  for_each = var.environment_account_ids
  
  name = "email-service-role-${each.key}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks_oidc_provider[each.key].arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks_oidc_provider[each.key].url, "https://", "")}:sub": "system:serviceaccount:email-service:email-service-sa"
          }
        }
      }
    ]
  })
  
  tags = {
    Environment = each.key
    Service     = "email-service"
  }
}

# Attach SES policy to Email Service role
resource "aws_iam_role_policy" "email_service_policy_attachment" {
  for_each = var.environment_account_ids
  
  name   = "email-service-ses-policy-${each.key}"
  role   = aws_iam_role.email_service_role[each.key].id
  policy = data.aws_iam_policy_document.email_service_policy.json
}

# ---------------------------------------------------------------------------------------------------------------------
# DATA SERVICE IAM ROLE
# ---------------------------------------------------------------------------------------------------------------------

# IAM policy for Data Service to access DynamoDB and other resources
data "aws_iam_policy_document" "data_service_policy" {
  statement {
    sid    = "AllowDataServiceS3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      for bucket_name in values(var.s3_bucket_names) : 
        "arn:aws:s3:::${bucket_name}/*",
      for bucket_name in values(var.s3_bucket_names) : 
        "arn:aws:s3:::${bucket_name}"
    ]
  }
  
  # Add KMS permissions for field-level encryption
  statement {
    sid    = "AllowDataServiceKMSAccess"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey"
    ]
    resources = ["*"] # This should be restricted to specific KMS keys in production
  }
}

# IAM role for Data Service
resource "aws_iam_role" "data_service_role" {
  for_each = var.environment_account_ids
  
  name = "data-service-role-${each.key}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks_oidc_provider[each.key].arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks_oidc_provider[each.key].url, "https://", "")}:sub": "system:serviceaccount:data-service:data-service-sa"
          }
        }
      }
    ]
  })
  
  tags = {
    Environment = each.key
    Service     = "data-service"
  }
}

# Attach policy to Data Service role
resource "aws_iam_role_policy" "data_service_policy_attachment" {
  for_each = var.environment_account_ids
  
  name   = "data-service-policy-${each.key}"
  role   = aws_iam_role.data_service_role[each.key].id
  policy = data.aws_iam_policy_document.data_service_policy.json
}

# ---------------------------------------------------------------------------------------------------------------------
# NOTIFICATION SERVICE IAM ROLE
# ---------------------------------------------------------------------------------------------------------------------

# IAM policy for Notification Service to access SNS and other resources
data "aws_iam_policy_document" "notification_service_policy" {
  statement {
    sid    = "AllowNotificationServiceSNSAccess"
    effect = "Allow"
    actions = [
      "sns:Publish",
      "sns:CreateTopic",
      "sns:Subscribe",
      "sns:Unsubscribe"
    ]
    resources = ["*"] # This should be restricted to specific SNS topics in production
  }
}

# IAM role for Notification Service
resource "aws_iam_role" "notification_service_role" {
  for_each = var.environment_account_ids
  
  name = "notification-service-role-${each.key}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks_oidc_provider[each.key].arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks_oidc_provider[each.key].url, "https://", "")}:sub": "system:serviceaccount:notification-service:notification-service-sa"
          }
        }
      }
    ]
  })
  
  tags = {
    Environment = each.key
    Service     = "notification-service"
  }
}

# Attach policy to Notification Service role
resource "aws_iam_role_policy" "notification_service_policy_attachment" {
  for_each = var.environment_account_ids
  
  name   = "notification-service-policy-${each.key}"
  role   = aws_iam_role.notification_service_role[each.key].id
  policy = data.aws_iam_policy_document.notification_service_policy.json
}

# ---------------------------------------------------------------------------------------------------------------------
# CROSS-ACCOUNT ROLES FOR ENVIRONMENT ACCESS
# ---------------------------------------------------------------------------------------------------------------------

# IAM policy for cross-account access
data "aws_iam_policy_document" "cross_account_assume_role_policy" {
  for_each = var.environment_account_ids
  
  statement {
    sid    = "AllowCrossAccountAccess"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${each.value}:root"]
    }
    actions = ["sts:AssumeRole"]
  }
}

# Cross-account role for CI/CD pipelines
resource "aws_iam_role" "cross_account_cicd_role" {
  for_each = var.environment_account_ids
  
  name               = "cross-account-cicd-role-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.cross_account_assume_role_policy[each.key].json
  
  tags = {
    Environment = each.key
    Purpose     = "CI/CD"
  }
}

# Policy for CI/CD cross-account role
data "aws_iam_policy_document" "cicd_policy" {
  statement {
    sid    = "AllowECRAccess"
    effect = "Allow"
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload"
    ]
    resources = ["*"]
  }
  
  statement {
    sid    = "AllowEKSAccess"
    effect = "Allow"
    actions = [
      "eks:DescribeCluster",
      "eks:ListClusters"
    ]
    resources = ["*"]
  }
  
  statement {
    sid    = "AllowS3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      for bucket_name in values(var.s3_bucket_names) : 
        "arn:aws:s3:::${bucket_name}/*",
      for bucket_name in values(var.s3_bucket_names) : 
        "arn:aws:s3:::${bucket_name}"
    ]
  }
}

# Attach policy to cross-account CI/CD role
resource "aws_iam_role_policy" "cross_account_cicd_policy_attachment" {
  for_each = var.environment_account_ids
  
  name   = "cross-account-cicd-policy-${each.key}"
  role   = aws_iam_role.cross_account_cicd_role[each.key].id
  policy = data.aws_iam_policy_document.cicd_policy.json
}

# ---------------------------------------------------------------------------------------------------------------------
# JWT AUTHENTICATION RESOURCES
# ---------------------------------------------------------------------------------------------------------------------

# KMS key for JWT token signing
resource "aws_kms_key" "jwt_signing_key" {
  description             = "KMS key for JWT token signing using RS256 algorithm"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = {
    Name = "jwt-signing-key"
    Purpose = "JWT Authentication"
  }
}

# KMS key alias for easier reference
resource "aws_kms_alias" "jwt_signing_key_alias" {
  name          = "alias/jwt-signing-key"
  target_key_id = aws_kms_key.jwt_signing_key.key_id
}

# SSM Parameter to store JWT configuration
resource "aws_ssm_parameter" "jwt_config" {
  name        = "/global/jwt/config"
  description = "JWT configuration for authentication"
  type        = "SecureString"
  value = jsonencode({
    algorithm    = var.jwt_algorithm
    token_expiry = var.jwt_token_expiry
    issuer       = "dollarfunding-mca"
    audience     = "mca-application-system"
    key_id       = aws_kms_key.jwt_signing_key.key_id
  })
  
  tags = {
    Name = "jwt-config"
    Purpose = "Authentication"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "document_service_role_arns" {
  description = "ARNs of the Document Service IAM roles"
  value       = { for env, role in aws_iam_role.document_service_role : env => role.arn }
}

output "ocr_service_role_arns" {
  description = "ARNs of the OCR Service IAM roles"
  value       = { for env, role in aws_iam_role.ocr_service_role : env => role.arn }
}

output "email_service_role_arns" {
  description = "ARNs of the Email Service IAM roles"
  value       = { for env, role in aws_iam_role.email_service_role : env => role.arn }
}

output "data_service_role_arns" {
  description = "ARNs of the Data Service IAM roles"
  value       = { for env, role in aws_iam_role.data_service_role : env => role.arn }
}

output "notification_service_role_arns" {
  description = "ARNs of the Notification Service IAM roles"
  value       = { for env, role in aws_iam_role.notification_service_role : env => role.arn }
}

output "cross_account_cicd_role_arns" {
  description = "ARNs of the cross-account CI/CD roles"
  value       = { for env, role in aws_iam_role.cross_account_cicd_role : env => role.arn }
}

output "jwt_signing_key_arn" {
  description = "ARN of the KMS key used for JWT signing"
  value       = aws_kms_key.jwt_signing_key.arn
}