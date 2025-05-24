# Global Security Configuration for MCA Application Processing System
# This file defines security resources that apply across all environments

# Provider configuration is assumed to be defined in a separate file

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
variable "environment" {
  description = "The environment for which to create resources (development, staging, production)"
  type        = string
  default     = "global"
}

variable "aws_region" {
  description = "The AWS region in which to create resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "allowed_ips" {
  description = "List of allowed IP addresses for administrative access"
  type        = list(string)
  default     = []
}

variable "key_rotation_period" {
  description = "Number of days for KMS key rotation"
  type        = number
  default     = 90
}

variable "token_expiry_minutes" {
  description = "JWT token expiry in minutes"
  type        = number
  default     = 60
}

variable "refresh_token_expiry_days" {
  description = "JWT refresh token expiry in days"
  type        = number
  default     = 7
}

# -----------------------------------------------------------------------------
# Locals
# -----------------------------------------------------------------------------
locals {
  common_tags = {
    Environment = var.environment
    Project     = "MCA-Application"
    ManagedBy   = "Terraform"
  }
  
  # Security settings based on technical specification
  security_settings = {
    jwt_algorithm      = "RS256"
    token_expiry       = var.token_expiry_minutes
    refresh_expiry     = var.refresh_token_expiry_days
    encryption_type    = "AES-256"
    tls_version        = "TLS1.3"
    rate_limit_auth    = 60  # requests per minute for authenticated users
    rate_limit_unauth  = 10  # requests per minute for unauthenticated users
  }
}

# -----------------------------------------------------------------------------
# AWS WAF Configuration for API Gateway and Application Load Balancer protection
# -----------------------------------------------------------------------------
resource "aws_wafv2_web_acl" "mca_global_waf" {
  name        = "mca-global-waf"
  description = "WAF ACL for MCA application protection"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # SQL Injection Protection Rule
  rule {
    name     = "SQLInjectionRule"
    priority = 1

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLInjectionRule"
      sampled_requests_enabled   = true
    }
  }

  # Common Vulnerabilities and Exposures Protection
  rule {
    name     = "CoreRuleSet"
    priority = 2

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CoreRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rate Limiting Rule - 60 requests per minute for authenticated users
  rule {
    name     = "RateLimitRule"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 60
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  # Bot Control Rule
  rule {
    name     = "BotControlRule"
    priority = 4

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesBotControlRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BotControlRule"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "mca-global-waf"
    sampled_requests_enabled   = true
  }

  tags = {
    Environment = "global"
    Service     = "mca-application"
  }
}

# -----------------------------------------------------------------------------
# Security Groups for different service tiers
# -----------------------------------------------------------------------------

# Frontend Security Group
resource "aws_security_group" "frontend_sg" {
  name        = "mca-frontend-sg"
  description = "Security group for frontend static hosting"

  # Allow HTTPS inbound from anywhere
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS inbound"
  }

  # Allow HTTP inbound from anywhere (will be redirected to HTTPS)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP inbound (redirected to HTTPS)"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "mca-frontend-sg"
    Environment = "global"
    Service     = "mca-frontend"
  }
}

# API Gateway Security Group
resource "aws_security_group" "api_gateway_sg" {
  name        = "mca-api-gateway-sg"
  description = "Security group for Kong API Gateway"

  # Allow HTTPS inbound from anywhere
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS inbound"
  }

  # Allow HTTP inbound from anywhere (will be redirected to HTTPS)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP inbound (redirected to HTTPS)"
  }

  # Allow all outbound traffic to backend services
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.0.0.0/8"]
    description = "All outbound traffic to backend services"
  }

  tags = {
    Name        = "mca-api-gateway-sg"
    Environment = "global"
    Service     = "mca-api-gateway"
  }
}

# Backend Services Security Group
resource "aws_security_group" "backend_services_sg" {
  name        = "mca-backend-services-sg"
  description = "Security group for backend microservices"

  # Allow HTTPS inbound from API Gateway only
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway_sg.id]
    description     = "HTTPS inbound from API Gateway"
  }

  # Allow internal service communication
  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    self            = true
    description     = "Internal service communication"
  }

  # Allow outbound to databases, message queues, and caches
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.0.0.0/8"]
    description = "Outbound to internal resources"
  }

  tags = {
    Name        = "mca-backend-services-sg"
    Environment = "global"
    Service     = "mca-backend"
  }
}

# Database Security Group
resource "aws_security_group" "database_sg" {
  name        = "mca-database-sg"
  description = "Security group for PostgreSQL databases"

  # Allow PostgreSQL inbound from backend services only
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_services_sg.id]
    description     = "PostgreSQL inbound from backend services"
  }

  # No outbound traffic needed for databases
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "mca-database-sg"
    Environment = "global"
    Service     = "mca-database"
  }
}

# Message Queue Security Group
resource "aws_security_group" "message_queue_sg" {
  name        = "mca-message-queue-sg"
  description = "Security group for RabbitMQ message queues"

  # Allow AMQP inbound from backend services only
  ingress {
    from_port       = 5671
    to_port         = 5671
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_services_sg.id]
    description     = "AMQP TLS inbound from backend services"
  }

  # Allow management console access from backend services
  ingress {
    from_port       = 15671
    to_port         = 15671
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_services_sg.id]
    description     = "Management console access (HTTPS)"
  }

  # No outbound traffic needed for message queues
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "mca-message-queue-sg"
    Environment = "global"
    Service     = "mca-rabbitmq"
  }
}

# Cache Security Group
resource "aws_security_group" "cache_sg" {
  name        = "mca-cache-sg"
  description = "Security group for Redis cache"

  # Allow Redis inbound from backend services only
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_services_sg.id]
    description     = "Redis inbound from backend services"
  }

  # No outbound traffic needed for caches
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "mca-cache-sg"
    Environment = "global"
    Service     = "mca-redis"
  }
}

# -----------------------------------------------------------------------------
# Network ACLs for traffic control
# -----------------------------------------------------------------------------
resource "aws_network_acl" "public_nacl" {
  # VPC ID will be provided by environment-specific configurations
  # vpc_id = var.vpc_id

  # Allow HTTP inbound
  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 80
    to_port    = 80
  }

  # Allow HTTPS inbound
  ingress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }

  # Allow ephemeral ports inbound for return traffic
  ingress {
    protocol   = "tcp"
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535
  }

  # Allow all outbound traffic
  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name        = "mca-public-nacl"
    Environment = "global"
  }
}

resource "aws_network_acl" "private_nacl" {
  # VPC ID will be provided by environment-specific configurations
  # vpc_id = var.vpc_id

  # Allow all inbound traffic from within VPC
  ingress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = "10.0.0.0/8"
    from_port  = 0
    to_port    = 0
  }

  # Allow all outbound traffic
  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name        = "mca-private-nacl"
    Environment = "global"
  }
}

# -----------------------------------------------------------------------------
# KMS Keys for Encryption
# -----------------------------------------------------------------------------

# Main encryption key for application data (AES-256)
resource "aws_kms_key" "mca_encryption_key" {
  description             = "KMS key for MCA application data encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  key_usage               = "ENCRYPT_DECRYPT"
  customer_master_key_spec = "SYMMETRIC_DEFAULT" # AES-256

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action   = "kms:*"
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = "${data.aws_caller_identity.current.account_id}"
          }
        }
      },
      {
        Sid    = "Allow use of the key for data service"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/mca-data-service-role"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "mca-encryption-key"
    Environment = "global"
    Service     = "mca-application"
  }
}

resource "aws_kms_alias" "mca_encryption_key_alias" {
  name          = "alias/mca-encryption-key"
  target_key_id = aws_kms_key.mca_encryption_key.key_id
}

# PII encryption key for field-level encryption
resource "aws_kms_key" "mca_pii_encryption_key" {
  description             = "KMS key for PII field-level encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  key_usage               = "ENCRYPT_DECRYPT"
  customer_master_key_spec = "SYMMETRIC_DEFAULT" # AES-256

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action   = "kms:*"
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = "${data.aws_caller_identity.current.account_id}"
          }
        }
      },
      {
        Sid    = "Allow use of the key for data service PII encryption"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/mca-data-service-role"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "mca-pii-encryption-key"
    Environment = "global"
    Service     = "mca-application"
    Purpose     = "PII-Encryption"
  }
}

resource "aws_kms_alias" "mca_pii_encryption_key_alias" {
  name          = "alias/mca-pii-encryption-key"
  target_key_id = aws_kms_key.mca_pii_encryption_key.key_id
}

# S3 storage encryption key
resource "aws_kms_key" "mca_s3_encryption_key" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  key_usage               = "ENCRYPT_DECRYPT"
  customer_master_key_spec = "SYMMETRIC_DEFAULT" # AES-256

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action   = "kms:*"
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = "${data.aws_caller_identity.current.account_id}"
          }
        }
      },
      {
        Sid    = "Allow use of the key for S3 service"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "Allow services to use the key for S3 access"
        Effect = "Allow"
        Principal = {
          AWS = [
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/mca-data-service-role",
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/mca-document-service-role",
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/mca-ocr-service-role"
          ]
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "mca-s3-encryption-key"
    Environment = "global"
    Service     = "mca-s3-storage"
  }
}

resource "aws_kms_alias" "mca_s3_encryption_key_alias" {
  name          = "alias/mca-s3-encryption-key"
  target_key_id = aws_kms_key.mca_s3_encryption_key.key_id
}

# -----------------------------------------------------------------------------
# IAM Roles and Policies
# -----------------------------------------------------------------------------

# IAM Role for Data Service with field-level encryption capabilities
resource "aws_iam_role" "data_service_role" {
  name = "mca-data-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "mca-data-service-role"
    Environment = "global"
    Service     = "mca-data-service"
  }
}

# IAM Policy for Data Service
resource "aws_iam_policy" "data_service_policy" {
  name        = "mca-data-service-policy"
  description = "Policy for MCA Data Service with encryption capabilities"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Effect   = "Allow"
        Resource = aws_kms_key.mca_encryption_key.arn
      },
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:s3:::mca-documents-*",
          "arn:aws:s3:::mca-documents-*/*"
        ]
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "data_service_policy_attachment" {
  role       = aws_iam_role.data_service_role.name
  policy_arn = aws_iam_policy.data_service_policy.arn
}

# IAM Role for Document Service
resource "aws_iam_role" "document_service_role" {
  name = "mca-document-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "mca-document-service-role"
    Environment = "global"
    Service     = "mca-document-service"
  }
}

# IAM Policy for Document Service
resource "aws_iam_policy" "document_service_policy" {
  name        = "mca-document-service-policy"
  description = "Policy for MCA Document Service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:s3:::mca-documents-*",
          "arn:aws:s3:::mca-documents-*/*"
        ]
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "document_service_policy_attachment" {
  role       = aws_iam_role.document_service_role.name
  policy_arn = aws_iam_policy.document_service_policy.arn
}

# IAM Role for OCR Service
resource "aws_iam_role" "ocr_service_role" {
  name = "mca-ocr-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "mca-ocr-service-role"
    Environment = "global"
    Service     = "mca-ocr-service"
  }
}

# IAM Policy for OCR Service
resource "aws_iam_policy" "ocr_service_policy" {
  name        = "mca-ocr-service-policy"
  description = "Policy for MCA OCR Service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:s3:::mca-documents-*",
          "arn:aws:s3:::mca-documents-*/*"
        ]
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "ocr_service_policy_attachment" {
  role       = aws_iam_role.ocr_service_role.name
  policy_arn = aws_iam_policy.ocr_service_policy.arn
}

# -----------------------------------------------------------------------------
# Security Monitoring and Alerting
# -----------------------------------------------------------------------------

# CloudWatch Log Group for Security Monitoring
resource "aws_cloudwatch_log_group" "security_log_group" {
  name              = "/mca/security"
  retention_in_days = 90

  tags = {
    Environment = "global"
    Service     = "mca-security"
  }
}

# SNS Topic for Security Alerts
resource "aws_sns_topic" "security_alerts" {
  name = "mca-security-alerts"
  
  tags = {
    Environment = "global"
    Service     = "mca-security"
  }
}

# CloudWatch Metric Alarm for WAF Blocked Requests
resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests" {
  alarm_name          = "mca-waf-blocked-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "This alarm monitors for high number of blocked requests by WAF"

  dimensions = {
    WebACL = aws_wafv2_web_acl.mca_global_waf.name
    Region = "us-east-1" # This should be parameterized based on deployment region
  }

  alarm_actions = [aws_sns_topic.security_alerts.arn]
  ok_actions    = [aws_sns_topic.security_alerts.arn]

  tags = {
    Environment = "global"
    Service     = "mca-security"
  }
}

# CloudWatch Metric Alarm for API Gateway 4xx Errors
resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx_errors" {
  alarm_name          = "mca-api-gateway-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 50
  alarm_description   = "This alarm monitors for high number of 4XX errors from API Gateway"

  dimensions = {
    ApiName = "mca-api-gateway" # This should be parameterized based on API Gateway name
  }

  alarm_actions = [aws_sns_topic.security_alerts.arn]
  ok_actions    = [aws_sns_topic.security_alerts.arn]

  tags = {
    Environment = "global"
    Service     = "mca-security"
  }
}

# CloudWatch Metric Alarm for Failed Authentication Attempts
resource "aws_cloudwatch_metric_alarm" "failed_auth_attempts" {
  alarm_name          = "mca-failed-auth-attempts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FailedAuthenticationCount"
  namespace           = "MCA/Security"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "This alarm monitors for high number of failed authentication attempts"

  alarm_actions = [aws_sns_topic.security_alerts.arn]
  ok_actions    = [aws_sns_topic.security_alerts.arn]

  tags = {
    Environment = "global"
    Service     = "mca-security"
  }
}

# CloudWatch Metric Alarm for S3 Bucket Policy Changes
resource "aws_cloudwatch_metric_alarm" "s3_bucket_policy_changes" {
  alarm_name          = "mca-s3-bucket-policy-changes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "S3BucketPolicyChanges"
  namespace           = "CloudTrail"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "This alarm monitors for changes to S3 bucket policies"

  alarm_actions = [aws_sns_topic.security_alerts.arn]
  ok_actions    = [aws_sns_topic.security_alerts.arn]

  tags = {
    Environment = "global"
    Service     = "mca-security"
  }
}

# CloudWatch Log Metric Filter for Suspicious Activities
resource "aws_cloudwatch_log_metric_filter" "suspicious_activities" {
  name           = "mca-suspicious-activities"
  pattern        = "\"SECURITY_ALERT\" \"SUSPICIOUS_ACTIVITY\""
  log_group_name = aws_cloudwatch_log_group.security_log_group.name

  metric_transformation {
    name      = "SuspiciousActivities"
    namespace = "MCA/Security"
    value     = "1"
  }
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "waf_acl_id" {
  description = "ID of the WAF ACL"
  value       = aws_wafv2_web_acl.mca_global_waf.id
}

output "waf_acl_arn" {
  description = "ARN of the WAF ACL"
  value       = aws_wafv2_web_acl.mca_global_waf.arn
}

output "security_groups" {
  description = "Map of security group IDs"
  value = {
    frontend       = aws_security_group.frontend_sg.id
    api_gateway    = aws_security_group.api_gateway_sg.id
    backend        = aws_security_group.backend_services_sg.id
    database       = aws_security_group.database_sg.id
    message_queue  = aws_security_group.message_queue_sg.id
    cache          = aws_security_group.cache_sg.id
  }
}

output "network_acls" {
  description = "Map of network ACL IDs"
  value = {
    public  = aws_network_acl.public_nacl.id
    private = aws_network_acl.private_nacl.id
  }
}

output "kms_keys" {
  description = "Map of KMS key ARNs"
  value = {
    application = aws_kms_key.mca_encryption_key.arn
    pii         = aws_kms_key.mca_pii_encryption_key.arn
    s3          = aws_kms_key.mca_s3_encryption_key.arn
  }
}

output "iam_roles" {
  description = "Map of IAM role ARNs"
  value = {
    data_service     = aws_iam_role.data_service_role.arn
    document_service = aws_iam_role.document_service_role.arn
    ocr_service      = aws_iam_role.ocr_service_role.arn
  }
}

output "security_alerts_topic" {
  description = "ARN of the security alerts SNS topic"
  value       = aws_sns_topic.security_alerts.arn
}

output "security_log_group" {
  description = "Name of the security log group"
  value       = aws_cloudwatch_log_group.security_log_group.name
}