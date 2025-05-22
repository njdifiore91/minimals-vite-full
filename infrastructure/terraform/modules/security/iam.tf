# IAM roles and policies for the MCA Application Processing System
# This file implements IAM roles with least-privilege permissions for each microservice

# ---------------------------------------------------------------------------------------------------------------------
# AWS ACCOUNT DATA
# ---------------------------------------------------------------------------------------------------------------------
data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------------------------------------------------
# IAM ROLES FOR MICROSERVICES
# ---------------------------------------------------------------------------------------------------------------------

# Email Service IAM Role
resource "aws_iam_role" "email_service" {
  name = "${local.name_prefix}-email-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "eks.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRoleWithWebIdentity",
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.eks_oidc_provider}"
        },
        Condition = {
          StringEquals = {
            "${var.eks_oidc_provider}:sub": "system:serviceaccount:${var.environment}:email-service-sa"
          }
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-email-service-role"
    Service = "email-service"
  })
}

# Document Service IAM Role
resource "aws_iam_role" "document_service" {
  name = "${local.name_prefix}-document-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "eks.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRoleWithWebIdentity",
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.eks_oidc_provider}"
        },
        Condition = {
          StringEquals = {
            "${var.eks_oidc_provider}:sub": "system:serviceaccount:${var.environment}:document-service-sa"
          }
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-document-service-role"
    Service = "document-service"
  })
}

# OCR Service IAM Role
resource "aws_iam_role" "ocr_service" {
  name = "${local.name_prefix}-ocr-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "eks.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRoleWithWebIdentity",
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.eks_oidc_provider}"
        },
        Condition = {
          StringEquals = {
            "${var.eks_oidc_provider}:sub": "system:serviceaccount:${var.environment}:ocr-service-sa"
          }
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ocr-service-role"
    Service = "ocr-service"
  })
}

# Data Service IAM Role
resource "aws_iam_role" "data_service" {
  name = "${local.name_prefix}-data-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "eks.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRoleWithWebIdentity",
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.eks_oidc_provider}"
        },
        Condition = {
          StringEquals = {
            "${var.eks_oidc_provider}:sub": "system:serviceaccount:${var.environment}:data-service-sa"
          }
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-data-service-role"
    Service = "data-service"
  })
}

# Notification Service IAM Role
resource "aws_iam_role" "notification_service" {
  name = "${local.name_prefix}-notification-service-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "eks.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRoleWithWebIdentity",
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.eks_oidc_provider}"
        },
        Condition = {
          StringEquals = {
            "${var.eks_oidc_provider}:sub": "system:serviceaccount:${var.environment}:notification-service-sa"
          }
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-notification-service-role"
    Service = "notification-service"
  })
}

# API Gateway IAM Role
resource "aws_iam_role" "api_gateway" {
  name = "${local.name_prefix}-api-gateway-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRoleWithWebIdentity",
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.eks_oidc_provider}"
        },
        Condition = {
          StringEquals = {
            "${var.eks_oidc_provider}:sub": "system:serviceaccount:${var.environment}:api-gateway-sa"
          }
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-gateway-role"
    Service = "api-gateway"
  })
}

# ---------------------------------------------------------------------------------------------------------------------
# IAM POLICIES FOR SPECIFIC PERMISSIONS
# ---------------------------------------------------------------------------------------------------------------------

# S3 Access Policy for Document-Related Services
resource "aws_iam_policy" "s3_document_access" {
  name        = "${local.name_prefix}-s3-document-access"
  description = "Policy for accessing document S3 buckets"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ],
        Resource = [
          for name, value in var.s3_bucket_names : 
            "arn:aws:s3:::${value}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket"
        ],
        Resource = [
          for name, value in var.s3_bucket_names : 
            "arn:aws:s3:::${value}"
        ]
      }
    ]
  })
}

# S3 Read-Only Access Policy for Services that only need to read documents
resource "aws_iam_policy" "s3_document_read_only" {
  name        = "${local.name_prefix}-s3-document-read-only"
  description = "Policy for read-only access to document S3 buckets"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          for name, value in var.s3_bucket_names : 
            "arn:aws:s3:::${value}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket"
        ],
        Resource = [
          for name, value in var.s3_bucket_names : 
            "arn:aws:s3:::${value}"
        ]
      }
    ]
  })
}

# KMS Access Policy for PII Encryption/Decryption
resource "aws_iam_policy" "kms_pii_access" {
  name        = "${local.name_prefix}-kms-pii-access"
  description = "Policy for accessing KMS keys for PII encryption/decryption"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
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
}

# Secrets Manager Access Policy for Email Service
resource "aws_iam_policy" "secrets_email_service" {
  name        = "${local.name_prefix}-secrets-email-service"
  description = "Policy for accessing email service secrets"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/email-service/*",
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/rabbitmq/*"
        ]
      }
    ]
  })
}

# Secrets Manager Access Policy for Document Service
resource "aws_iam_policy" "secrets_document_service" {
  name        = "${local.name_prefix}-secrets-document-service"
  description = "Policy for accessing document service secrets"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/rabbitmq/*"
        ]
      }
    ]
  })
}

# Secrets Manager Access Policy for OCR Service
resource "aws_iam_policy" "secrets_ocr_service" {
  name        = "${local.name_prefix}-secrets-ocr-service"
  description = "Policy for accessing OCR service secrets"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/rabbitmq/*"
        ]
      }
    ]
  })
}

# Secrets Manager Access Policy for Data Service
resource "aws_iam_policy" "secrets_data_service" {
  name        = "${local.name_prefix}-secrets-data-service"
  description = "Policy for accessing data service secrets"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/rabbitmq/*",
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/redis/*"
        ]
      }
    ]
  })
}

# Secrets Manager Access Policy for Notification Service
resource "aws_iam_policy" "secrets_notification_service" {
  name        = "${local.name_prefix}-secrets-notification-service"
  description = "Policy for accessing notification service secrets"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/rabbitmq/*",
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/notification-service/*"
        ]
      }
    ]
  })
}

# Secrets Manager Access Policy for API Gateway
resource "aws_iam_policy" "secrets_api_gateway" {
  name        = "${local.name_prefix}-secrets-api-gateway"
  description = "Policy for accessing API gateway secrets"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mca/jwt/*"
        ]
      }
    ]
  })
}

# SES Access Policy for Email Service
resource "aws_iam_policy" "ses_email_service" {
  name        = "${local.name_prefix}-ses-email-service"
  description = "Policy for accessing SES for email service"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ses:GetIdentityVerificationAttributes",
          "ses:SendEmail",
          "ses:SendRawEmail"
        ],
        Resource = "*"
      }
    ]
  })
}

# SQS Access Policy for Notification Service
resource "aws_iam_policy" "sqs_notification_service" {
  name        = "${local.name_prefix}-sqs-notification-service"
  description = "Policy for accessing SQS for notification service"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ],
        Resource = "arn:aws:sqs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${local.name_prefix}-*"
      }
    ]
  })
}

# SNS Access Policy for Notification Service
resource "aws_iam_policy" "sns_notification_service" {
  name        = "${local.name_prefix}-sns-notification-service"
  description = "Policy for accessing SNS for notification service"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "sns:Publish",
          "sns:Subscribe",
          "sns:Unsubscribe",
          "sns:ListSubscriptionsByTopic"
        ],
        Resource = "arn:aws:sns:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${local.name_prefix}-*"
      }
    ]
  })
}

# JWT Key Access Policy for API Gateway
resource "aws_iam_policy" "jwt_key_api_gateway" {
  name        = "${local.name_prefix}-jwt-key-api-gateway"
  description = "Policy for accessing JWT keys for API Gateway"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ssm:GetParameter"
        ],
        Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/mca/jwt/public-key"
      }
    ]
  })
}

# ---------------------------------------------------------------------------------------------------------------------
# POLICY ATTACHMENTS
# ---------------------------------------------------------------------------------------------------------------------

# Email Service Policy Attachments
resource "aws_iam_role_policy_attachment" "email_service_ses" {
  role       = aws_iam_role.email_service.name
  policy_arn = aws_iam_policy.ses_email_service.arn
}

resource "aws_iam_role_policy_attachment" "email_service_secrets" {
  role       = aws_iam_role.email_service.name
  policy_arn = aws_iam_policy.secrets_email_service.arn
}

# Document Service Policy Attachments
resource "aws_iam_role_policy_attachment" "document_service_s3" {
  role       = aws_iam_role.document_service.name
  policy_arn = aws_iam_policy.s3_document_access.arn
}

resource "aws_iam_role_policy_attachment" "document_service_secrets" {
  role       = aws_iam_role.document_service.name
  policy_arn = aws_iam_policy.secrets_document_service.arn
}

# OCR Service Policy Attachments
resource "aws_iam_role_policy_attachment" "ocr_service_s3" {
  role       = aws_iam_role.ocr_service.name
  policy_arn = aws_iam_policy.s3_document_access.arn
}

resource "aws_iam_role_policy_attachment" "ocr_service_secrets" {
  role       = aws_iam_role.ocr_service.name
  policy_arn = aws_iam_policy.secrets_ocr_service.arn
}

# Data Service Policy Attachments
resource "aws_iam_role_policy_attachment" "data_service_kms" {
  role       = aws_iam_role.data_service.name
  policy_arn = aws_iam_policy.kms_pii_access.arn
}

resource "aws_iam_role_policy_attachment" "data_service_secrets" {
  role       = aws_iam_role.data_service.name
  policy_arn = aws_iam_policy.secrets_data_service.arn
}

resource "aws_iam_role_policy_attachment" "data_service_s3_read" {
  role       = aws_iam_role.data_service.name
  policy_arn = aws_iam_policy.s3_document_read_only.arn
}

# Notification Service Policy Attachments
resource "aws_iam_role_policy_attachment" "notification_service_sqs" {
  role       = aws_iam_role.notification_service.name
  policy_arn = aws_iam_policy.sqs_notification_service.arn
}

resource "aws_iam_role_policy_attachment" "notification_service_sns" {
  role       = aws_iam_role.notification_service.name
  policy_arn = aws_iam_policy.sns_notification_service.arn
}

resource "aws_iam_role_policy_attachment" "notification_service_secrets" {
  role       = aws_iam_role.notification_service.name
  policy_arn = aws_iam_policy.secrets_notification_service.arn
}

# API Gateway Policy Attachments
resource "aws_iam_role_policy_attachment" "api_gateway_jwt" {
  role       = aws_iam_role.api_gateway.name
  policy_arn = aws_iam_policy.jwt_key_api_gateway.arn
}

resource "aws_iam_role_policy_attachment" "api_gateway_secrets" {
  role       = aws_iam_role.api_gateway.name
  policy_arn = aws_iam_policy.secrets_api_gateway.arn
}

# Create a KMS policy for S3 encryption if using KMS
resource "aws_iam_policy" "s3_kms_access" {
  count       = var.s3_encryption_type == "aws:kms" ? 1 : 0
  name        = "${local.name_prefix}-s3-kms-access"
  description = "Policy for accessing the S3 KMS encryption key"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        Resource = "*",
        Condition = {
          StringLike = {
            "kms:ViaService": "s3.*.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Attach KMS S3 access policy if using KMS encryption
resource "aws_iam_role_policy_attachment" "document_service_kms_s3" {
  count      = var.s3_encryption_type == "aws:kms" ? 1 : 0
  role       = aws_iam_role.document_service.name
  policy_arn = aws_iam_policy.s3_kms_access[0].arn
}

resource "aws_iam_role_policy_attachment" "ocr_service_kms_s3" {
  count      = var.s3_encryption_type == "aws:kms" ? 1 : 0
  role       = aws_iam_role.ocr_service.name
  policy_arn = aws_iam_policy.s3_kms_access[0].arn
}

# ---------------------------------------------------------------------------------------------------------------------
# ADDITIONAL DATA SOURCES
# ---------------------------------------------------------------------------------------------------------------------
data "aws_region" "current" {}

# ---------------------------------------------------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "email_service_role_arn" {
  description = "ARN of the IAM role for the Email Service"
  value       = aws_iam_role.email_service.arn
}

output "document_service_role_arn" {
  description = "ARN of the IAM role for the Document Service"
  value       = aws_iam_role.document_service.arn
}

output "ocr_service_role_arn" {
  description = "ARN of the IAM role for the OCR Service"
  value       = aws_iam_role.ocr_service.arn
}

output "data_service_role_arn" {
  description = "ARN of the IAM role for the Data Service"
  value       = aws_iam_role.data_service.arn
}

output "notification_service_role_arn" {
  description = "ARN of the IAM role for the Notification Service"
  value       = aws_iam_role.notification_service.arn
}

output "api_gateway_role_arn" {
  description = "ARN of the IAM role for the API Gateway"
  value       = aws_iam_role.api_gateway.arn
}

output "s3_document_access_policy_arn" {
  description = "ARN of the IAM policy for S3 document access"
  value       = aws_iam_policy.s3_document_access.arn
}

output "s3_document_read_only_policy_arn" {
  description = "ARN of the IAM policy for S3 document read-only access"
  value       = aws_iam_policy.s3_document_read_only.arn
}

output "kms_pii_access_policy_arn" {
  description = "ARN of the IAM policy for KMS PII access"
  value       = aws_iam_policy.kms_pii_access.arn
}