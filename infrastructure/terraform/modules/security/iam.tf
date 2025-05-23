# IAM Roles and Policies for MCA Application Processing System
#
# This file implements IAM roles and policies with least-privilege permissions for each microservice,
# including specific policies for S3 access, KMS encryption/decryption, and Secrets Manager access.
# It follows the principle of least privilege as required by the security architecture.

# Variables for IAM configuration
variable "region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "enable_cross_account_access" {
  description = "Whether to enable cross-account access for IAM roles"
  type        = bool
  default     = false
}

variable "trusted_account_ids" {
  description = "List of AWS account IDs that are allowed to assume the IAM roles"
  type        = list(string)
  default     = []
}

variable "s3_document_bucket_name" {
  description = "Name of the S3 bucket used for document storage"
  type        = string
  default     = ""
}

variable "s3_sensitive_document_bucket_name" {
  description = "Name of the S3 bucket used for sensitive document storage"
  type        = string
  default     = ""
}

# Local variables for IAM configuration
locals {
  # Determine S3 bucket names based on environment if not provided
  document_bucket_name = var.s3_document_bucket_name != "" ? var.s3_document_bucket_name : "mca-documents-${var.environment}"
  sensitive_document_bucket_name = var.s3_sensitive_document_bucket_name != "" ? var.s3_sensitive_document_bucket_name : "mca-sensitive-documents-${var.environment}"
  
  # Service-specific settings
  service_config = {
    "email-service" = {
      description = "IAM role for Email Service"
      requires_s3_access = false
      requires_ses_access = true
      requires_kms_access = false
      requires_secrets_access = true
      requires_sqs_access = true
      requires_dynamodb_access = false
      requires_rds_access = false
    },
    "document-service" = {
      description = "IAM role for Document Service"
      requires_s3_access = true
      requires_ses_access = false
      requires_kms_access = true
      requires_secrets_access = true
      requires_sqs_access = true
      requires_dynamodb_access = false
      requires_rds_access = false
    },
    "ocr-service" = {
      description = "IAM role for OCR Service"
      requires_s3_access = true
      requires_ses_access = false
      requires_kms_access = true
      requires_secrets_access = true
      requires_sqs_access = true
      requires_dynamodb_access = false
      requires_rds_access = false
    },
    "data-service" = {
      description = "IAM role for Data Service"
      requires_s3_access = false
      requires_ses_access = false
      requires_kms_access = true
      requires_secrets_access = true
      requires_sqs_access = true
      requires_dynamodb_access = false
      requires_rds_access = true
    },
    "notification-service" = {
      description = "IAM role for Notification Service"
      requires_s3_access = false
      requires_ses_access = true
      requires_kms_access = false
      requires_secrets_access = true
      requires_sqs_access = true
      requires_dynamodb_access = true
      requires_rds_access = false
    },
    "api-gateway" = {
      description = "IAM role for API Gateway"
      requires_s3_access = false
      requires_ses_access = false
      requires_kms_access = false
      requires_secrets_access = true
      requires_sqs_access = false
      requires_dynamodb_access = false
      requires_rds_access = false
    }
  }
  
  # Define common actions for each service type to ensure least privilege
  s3_actions = {
    read = [
      "s3:GetObject",
      "s3:ListBucket"
    ],
    write = [
      "s3:PutObject",
      "s3:DeleteObject"
    ],
    tagging = [
      "s3:GetObjectTagging",
      "s3:PutObjectTagging"
    ]
  }
  
  kms_actions = {
    read = [
      "kms:DescribeKey"
    ],
    encrypt = [
      "kms:Encrypt",
      "kms:GenerateDataKey*"
    ],
    decrypt = [
      "kms:Decrypt"
    ],
    reencrypt = [
      "kms:ReEncrypt*"
    ]
  }
  
  secrets_actions = [
    "secretsmanager:GetSecretValue",
    "secretsmanager:DescribeSecret"
  ]
  
  sqs_actions = {
    producer = [
      "sqs:SendMessage",
      "sqs:GetQueueUrl",
      "sqs:GetQueueAttributes"
    ],
    consumer = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueUrl",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility"
    ]
  }
}

# S3 Access Policy for document-related services
resource "aws_iam_policy" "s3_document_access" {
  name        = "${local.name_prefix}-s3-document-access-policy"
  description = "Policy for accessing S3 document buckets with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = concat(local.s3_actions.read, local.s3_actions.write, local.s3_actions.tagging),
        Resource = [
          "arn:aws:s3:::${local.document_bucket_name}/*",
          "arn:aws:s3:::${local.sensitive_document_bucket_name}/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = ["s3:ListBucket"],
        Resource = [
          "arn:aws:s3:::${local.document_bucket_name}",
          "arn:aws:s3:::${local.sensitive_document_bucket_name}"
        ]
      },
      {
        Effect   = "Allow",
        Action   = ["s3:ListAllMyBuckets"],
        Resource = ["*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-s3-document-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# KMS Access Policy for encryption/decryption operations
resource "aws_iam_policy" "kms_data_access" {
  name        = "${local.name_prefix}-kms-data-access-policy"
  description = "Policy for using KMS keys for data encryption/decryption with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = flatten([local.kms_actions.read, local.kms_actions.encrypt, local.kms_actions.decrypt, local.kms_actions.reencrypt]),
        Resource = [aws_kms_key.data_encryption_key.arn]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-kms-data-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# Secrets Manager Access Policy for credential retrieval
resource "aws_iam_policy" "secrets_access" {
  name        = "${local.name_prefix}-secrets-access-policy"
  description = "Policy for accessing secrets in AWS Secrets Manager with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = local.secrets_actions,
        Resource = ["arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-secrets-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# SES Access Policy for email services
resource "aws_iam_policy" "ses_access" {
  name        = "${local.name_prefix}-ses-access-policy"
  description = "Policy for sending emails via Amazon SES with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ],
        Resource = ["*"],
        Condition = {
          StringEquals = {
            "ses:FromAddress": ["submissions@dollarfunding.com", "notifications@dollarfunding.com"]
          }
        }
      },
      {
        Effect   = "Allow",
        Action   = ["ses:GetIdentityVerificationAttributes"],
        Resource = ["*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-ses-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# SQS Access Policy for message queue operations
resource "aws_iam_policy" "sqs_producer_access" {
  name        = "${local.name_prefix}-sqs-producer-access-policy"
  description = "Policy for producing messages to SQS queues with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = local.sqs_actions.producer,
        Resource = ["arn:aws:sqs:${var.region}:${data.aws_caller_identity.current.account_id}:${local.name_prefix}*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-sqs-producer-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

resource "aws_iam_policy" "sqs_consumer_access" {
  name        = "${local.name_prefix}-sqs-consumer-access-policy"
  description = "Policy for consuming messages from SQS queues with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = local.sqs_actions.consumer,
        Resource = ["arn:aws:sqs:${var.region}:${data.aws_caller_identity.current.account_id}:${local.name_prefix}*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-sqs-consumer-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# DynamoDB Access Policy for notification service
resource "aws_iam_policy" "dynamodb_webhook_access" {
  name        = "${local.name_prefix}-dynamodb-webhook-access-policy"
  description = "Policy for accessing DynamoDB tables for webhook configuration with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ],
        Resource = [
          "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${local.name_prefix}-webhooks",
          "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${local.name_prefix}-webhooks/index/*"
        ]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-dynamodb-webhook-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# RDS Access Policy for data service
resource "aws_iam_policy" "rds_access" {
  name        = "${local.name_prefix}-rds-access-policy"
  description = "Policy for accessing RDS instances with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "rds:DescribeDBInstances",
          "rds:DescribeDBClusters",
          "rds:DescribeDBClusterEndpoints"
        ],
        Resource = ["*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-rds-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# Email Service specific policy for IMAP access
resource "aws_iam_policy" "email_service_specific" {
  name        = "${local.name_prefix}-email-service-specific-policy"
  description = "Specific policy for Email Service operations with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "ses:GetIdentityMailFromDomainAttributes",
          "ses:ListIdentities"
        ],
        Resource = ["*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-email-service-specific-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# Document Service specific policy
resource "aws_iam_policy" "document_service_specific" {
  name        = "${local.name_prefix}-document-service-specific-policy"
  description = "Specific policy for Document Service operations with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "s3:GetObjectVersion",
          "s3:GetObjectVersionTagging"
        ],
        Resource = [
          "arn:aws:s3:::${local.document_bucket_name}/*",
          "arn:aws:s3:::${local.sensitive_document_bucket_name}/*"
        ]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-document-service-specific-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# OCR Service specific policy
resource "aws_iam_policy" "ocr_service_specific" {
  name        = "${local.name_prefix}-ocr-service-specific-policy"
  description = "Specific policy for OCR Service operations with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "s3:GetObjectVersion",
          "s3:GetObjectVersionTagging"
        ],
        Resource = [
          "arn:aws:s3:::${local.document_bucket_name}/*",
          "arn:aws:s3:::${local.sensitive_document_bucket_name}/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = [
          "rekognition:DetectText",
          "textract:AnalyzeDocument",
          "textract:DetectDocumentText",
          "textract:GetDocumentAnalysis",
          "textract:StartDocumentAnalysis",
          "textract:StartDocumentTextDetection"
        ],
        Resource = ["*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-ocr-service-specific-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# Notification Service specific policy
resource "aws_iam_policy" "notification_service_specific" {
  name        = "${local.name_prefix}-notification-service-specific-policy"
  description = "Specific policy for Notification Service operations with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "sns:Publish",
          "sns:Subscribe",
          "sns:Unsubscribe",
          "sns:ListSubscriptionsByTopic"
        ],
        Resource = ["arn:aws:sns:${var.region}:${data.aws_caller_identity.current.account_id}:${local.name_prefix}*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-notification-service-specific-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# Data Service specific policy
resource "aws_iam_policy" "data_service_specific" {
  name        = "${local.name_prefix}-data-service-specific-policy"
  description = "Specific policy for Data Service operations with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = flatten([local.kms_actions.encrypt, local.kms_actions.decrypt]),
        Resource = [aws_kms_key.data_encryption_key.arn]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-data-service-specific-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# API Gateway specific policy
resource "aws_iam_policy" "api_gateway_specific" {
  name        = "${local.name_prefix}-api-gateway-specific-policy"
  description = "Specific policy for API Gateway operations with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "execute-api:Invoke",
          "execute-api:ManageConnections"
        ],
        Resource = ["arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:*"]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-api-gateway-specific-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# CloudWatch Logs access for all services
resource "aws_iam_policy" "cloudwatch_logs_access" {
  name        = "${local.name_prefix}-cloudwatch-logs-access-policy"
  description = "Policy for writing to CloudWatch Logs with least privilege"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ],
        Resource = [
          "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name_prefix}*",
          "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name_prefix}*:log-stream:*",
          "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/eks/${local.name_prefix}*",
          "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/eks/${local.name_prefix}*:log-stream:*"
        ]
      }
    ]
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-cloudwatch-logs-access-policy"
      Type = "IAM-Policy"
    },
    var.resource_tags
  )
}

# Attach policies to roles based on service-specific requirements

# Attach S3 document access policy to document-related services
resource "aws_iam_role_policy_attachment" "s3_document_access_attachment" {
  for_each = { for k, v in local.service_config : k => v if v.requires_s3_access }
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.s3_document_access.arn
}

# Attach KMS data access policy to services that need encryption/decryption
resource "aws_iam_role_policy_attachment" "kms_data_access_attachment" {
  for_each = { for k, v in local.service_config : k => v if v.requires_kms_access }
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.kms_data_access.arn
}

# Attach Secrets Manager access policy to services that need credentials
resource "aws_iam_role_policy_attachment" "secrets_access_attachment" {
  for_each = { for k, v in local.service_config : k => v if v.requires_secrets_access }
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.secrets_access.arn
}

# Attach SES access policy to email-related services
resource "aws_iam_role_policy_attachment" "ses_access_attachment" {
  for_each = { for k, v in local.service_config : k => v if v.requires_ses_access }
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.ses_access.arn
}

# Attach SQS producer access policy to services that send messages
resource "aws_iam_role_policy_attachment" "sqs_producer_access_attachment" {
  for_each = { for k, v in local.service_config : k => v if v.requires_sqs_access }
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.sqs_producer_access.arn
}

# Attach SQS consumer access policy to services that receive messages
resource "aws_iam_role_policy_attachment" "sqs_consumer_access_attachment" {
  for_each = { for k, v in local.service_config : k => v if v.requires_sqs_access }
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.sqs_consumer_access.arn
}

# Attach DynamoDB access policy to notification service
resource "aws_iam_role_policy_attachment" "dynamodb_webhook_access_attachment" {
  for_each = { for k, v in local.service_config : k => v if v.requires_dynamodb_access }
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.dynamodb_webhook_access.arn
}

# Attach RDS access policy to data service
resource "aws_iam_role_policy_attachment" "rds_access_attachment" {
  for_each = { for k, v in local.service_config : k => v if v.requires_rds_access }
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.rds_access.arn
}

# Attach service-specific policies
resource "aws_iam_role_policy_attachment" "email_service_specific_attachment" {
  role       = aws_iam_role.service_roles["email-service"].name
  policy_arn = aws_iam_policy.email_service_specific.arn
}

resource "aws_iam_role_policy_attachment" "document_service_specific_attachment" {
  role       = aws_iam_role.service_roles["document-service"].name
  policy_arn = aws_iam_policy.document_service_specific.arn
}

resource "aws_iam_role_policy_attachment" "ocr_service_specific_attachment" {
  role       = aws_iam_role.service_roles["ocr-service"].name
  policy_arn = aws_iam_policy.ocr_service_specific.arn
}

resource "aws_iam_role_policy_attachment" "notification_service_specific_attachment" {
  role       = aws_iam_role.service_roles["notification-service"].name
  policy_arn = aws_iam_policy.notification_service_specific.arn
}

resource "aws_iam_role_policy_attachment" "data_service_specific_attachment" {
  role       = aws_iam_role.service_roles["data-service"].name
  policy_arn = aws_iam_policy.data_service_specific.arn
}

resource "aws_iam_role_policy_attachment" "api_gateway_specific_attachment" {
  role       = aws_iam_role.service_roles["api-gateway"].name
  policy_arn = aws_iam_policy.api_gateway_specific.arn
}

# Attach CloudWatch Logs access to all service roles
resource "aws_iam_role_policy_attachment" "cloudwatch_logs_access_attachment" {
  for_each = local.service_config
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.cloudwatch_logs_access.arn
}

# Outputs for IAM roles and policies
output "service_role_arns" {
  description = "Map of service names to their IAM role ARNs"
  value       = { for k, v in aws_iam_role.service_roles : k => v.arn }
}

output "service_role_names" {
  description = "Map of service names to their IAM role names"
  value       = { for k, v in aws_iam_role.service_roles : k => v.name }
}

output "policy_arns" {
  description = "Map of policy names to their ARNs"
  value       = {
    s3_document_access = aws_iam_policy.s3_document_access.arn,
    kms_data_access = aws_iam_policy.kms_data_access.arn,
    secrets_access = aws_iam_policy.secrets_access.arn,
    ses_access = aws_iam_policy.ses_access.arn,
    sqs_producer_access = aws_iam_policy.sqs_producer_access.arn,
    sqs_consumer_access = aws_iam_policy.sqs_consumer_access.arn,
    dynamodb_webhook_access = aws_iam_policy.dynamodb_webhook_access.arn,
    rds_access = aws_iam_policy.rds_access.arn,
    cloudwatch_logs_access = aws_iam_policy.cloudwatch_logs_access.arn
  }
}