# IAM roles, policies, and service accounts shared across all environments
# This file defines global IAM resources needed by various services to interact with cloud resources

# -----------------------------------------------------------------------------
# IAM Roles for Kubernetes Service Accounts (IRSA)
# These roles enable Kubernetes service accounts to assume AWS IAM roles
# -----------------------------------------------------------------------------

# OIDC Provider for EKS clusters to enable IAM roles for service accounts
resource "aws_iam_openid_connect_provider" "eks_oidc_provider" {
  url             = var.eks_oidc_provider_url
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = var.eks_oidc_thumbprints

  tags = {
    Name        = "${var.organization_prefix}-eks-oidc-provider"
    Environment = "global"
    Terraform   = "true"
  }
}

# -----------------------------------------------------------------------------
# Cross-Account IAM Roles
# These roles allow access between different environment accounts
# -----------------------------------------------------------------------------

# Role that allows the CI/CD pipeline to deploy to all environments
resource "aws_iam_role" "cicd_deployment_role" {
  name = "${var.organization_prefix}-cicd-deployment-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = var.cicd_account_arns
        }
      }
    ]
  })

  tags = {
    Name        = "${var.organization_prefix}-cicd-deployment-role"
    Environment = "global"
    Terraform   = "true"
  }
}

# Policy for CI/CD deployment role with permissions to deploy to all environments
resource "aws_iam_policy" "cicd_deployment_policy" {
  name        = "${var.organization_prefix}-cicd-deployment-policy"
  description = "Policy for CI/CD pipeline to deploy to all environments"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "eks:DescribeCluster",
          "eks:ListClusters",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.organization_prefix}-*-artifacts/*",
          "arn:aws:s3:::${var.organization_prefix}-*-artifacts"
        ]
      }
    ]
  })
}

# Attach the deployment policy to the CI/CD role
resource "aws_iam_role_policy_attachment" "cicd_deployment_attachment" {
  role       = aws_iam_role.cicd_deployment_role.name
  policy_arn = aws_iam_policy.cicd_deployment_policy.arn
}

# -----------------------------------------------------------------------------
# Global S3 Access Policies
# These policies define access to S3 buckets shared across environments
# -----------------------------------------------------------------------------

# Policy for read-only access to document storage buckets
resource "aws_iam_policy" "s3_document_read_policy" {
  name        = "${var.organization_prefix}-s3-document-read-policy"
  description = "Policy for read-only access to document storage buckets"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.organization_prefix}-*-documents/*",
          "arn:aws:s3:::${var.organization_prefix}-*-documents"
        ]
      }
    ]
  })
}

# Policy for read-write access to document storage buckets
resource "aws_iam_policy" "s3_document_readwrite_policy" {
  name        = "${var.organization_prefix}-s3-document-readwrite-policy"
  description = "Policy for read-write access to document storage buckets"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.organization_prefix}-*-documents/*",
          "arn:aws:s3:::${var.organization_prefix}-*-documents"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Service-Specific IAM Policies
# These policies define permissions for specific services across environments
# -----------------------------------------------------------------------------

# Policy for Email Service to access SES and S3
resource "aws_iam_policy" "email_service_policy" {
  name        = "${var.organization_prefix}-email-service-policy"
  description = "Policy for Email Service to access SES and S3"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.organization_prefix}-*-documents/email-attachments/*"
        ]
      }
    ]
  })
}

# Policy for Document Service to access S3 and machine learning services
resource "aws_iam_policy" "document_service_policy" {
  name        = "${var.organization_prefix}-document-service-policy"
  description = "Policy for Document Service to access S3 and ML services"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.organization_prefix}-*-documents/*",
          "arn:aws:s3:::${var.organization_prefix}-*-documents"
        ]
      },
      {
        Action = [
          "rekognition:DetectText",
          "rekognition:AnalyzeDocument",
          "textract:AnalyzeDocument",
          "textract:DetectDocumentText"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Policy for OCR Service to access S3 and machine learning services
resource "aws_iam_policy" "ocr_service_policy" {
  name        = "${var.organization_prefix}-ocr-service-policy"
  description = "Policy for OCR Service to access S3 and ML services"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.organization_prefix}-*-documents/*"
        ]
      },
      {
        Action = [
          "rekognition:DetectText",
          "rekognition:AnalyzeDocument",
          "textract:AnalyzeDocument",
          "textract:DetectDocumentText"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Policy for Data Service to access RDS and S3
resource "aws_iam_policy" "data_service_policy" {
  name        = "${var.organization_prefix}-data-service-policy"
  description = "Policy for Data Service to access RDS and S3"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "rds:DescribeDBInstances",
          "rds:DescribeDBClusters"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "s3:GetObject"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.organization_prefix}-*-documents/*"
        ]
      },
      {
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Effect   = "Allow"
        Resource = var.pii_encryption_key_arns
      }
    ]
  })
}

# Policy for Notification Service to access SNS and SQS
resource "aws_iam_policy" "notification_service_policy" {
  name        = "${var.organization_prefix}-notification-service-policy"
  description = "Policy for Notification Service to access SNS and SQS"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sns:Publish",
          "sns:CreateTopic",
          "sns:Subscribe",
          "sns:Unsubscribe"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:sns:*:*:${var.organization_prefix}-*"
      },
      {
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueUrl",
          "sqs:GetQueueAttributes"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:sqs:*:*:${var.organization_prefix}-*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# JWT Authentication IAM Resources
# These resources support JWT authentication with RS256 algorithm
# -----------------------------------------------------------------------------

# IAM user for JWT token signing (used by API Gateway)
resource "aws_iam_user" "jwt_signing_user" {
  name = "${var.organization_prefix}-jwt-signing-user"
  path = "/system/"

  tags = {
    Name        = "${var.organization_prefix}-jwt-signing-user"
    Environment = "global"
    Terraform   = "true"
  }
}

# Policy for JWT signing user to access KMS for signing operations
resource "aws_iam_policy" "jwt_signing_policy" {
  name        = "${var.organization_prefix}-jwt-signing-policy"
  description = "Policy for JWT signing operations using KMS"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "kms:Sign",
          "kms:Verify",
          "kms:GetPublicKey"
        ]
        Effect   = "Allow"
        Resource = var.jwt_signing_key_arns
      }
    ]
  })
}

# Attach the JWT signing policy to the JWT signing user
resource "aws_iam_user_policy_attachment" "jwt_signing_attachment" {
  user       = aws_iam_user.jwt_signing_user.name
  policy_arn = aws_iam_policy.jwt_signing_policy.arn
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "organization_prefix" {
  description = "Prefix used for all resource names"
  type        = string
  default     = "dollarfunding-mca"
}

variable "eks_oidc_provider_url" {
  description = "URL of the OIDC provider for EKS clusters"
  type        = string
}

variable "eks_oidc_thumbprints" {
  description = "Thumbprints of the OIDC provider for EKS clusters"
  type        = list(string)
}

variable "cicd_account_arns" {
  description = "ARNs of the CI/CD accounts that can assume the deployment role"
  type        = list(string)
}

variable "pii_encryption_key_arns" {
  description = "ARNs of the KMS keys used for PII encryption"
  type        = list(string)
}

variable "jwt_signing_key_arns" {
  description = "ARNs of the KMS keys used for JWT signing"
  type        = list(string)
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "cicd_deployment_role_arn" {
  description = "ARN of the CI/CD deployment role"
  value       = aws_iam_role.cicd_deployment_role.arn
}

output "s3_document_read_policy_arn" {
  description = "ARN of the S3 document read-only policy"
  value       = aws_iam_policy.s3_document_read_policy.arn
}

output "s3_document_readwrite_policy_arn" {
  description = "ARN of the S3 document read-write policy"
  value       = aws_iam_policy.s3_document_readwrite_policy.arn
}

output "email_service_policy_arn" {
  description = "ARN of the Email Service policy"
  value       = aws_iam_policy.email_service_policy.arn
}

output "document_service_policy_arn" {
  description = "ARN of the Document Service policy"
  value       = aws_iam_policy.document_service_policy.arn
}

output "ocr_service_policy_arn" {
  description = "ARN of the OCR Service policy"
  value       = aws_iam_policy.ocr_service_policy.arn
}

output "data_service_policy_arn" {
  description = "ARN of the Data Service policy"
  value       = aws_iam_policy.data_service_policy.arn
}

output "notification_service_policy_arn" {
  description = "ARN of the Notification Service policy"
  value       = aws_iam_policy.notification_service_policy.arn
}

output "jwt_signing_user_arn" {
  description = "ARN of the JWT signing user"
  value       = aws_iam_user.jwt_signing_user.arn
}

output "eks_oidc_provider_arn" {
  description = "ARN of the EKS OIDC provider"
  value       = aws_iam_openid_connect_provider.eks_oidc_provider.arn
}