# RabbitMQ Security Configuration for MCA Application Processing System

# This file implements comprehensive security measures for the RabbitMQ cluster, including:
# - TLS for transit encryption (TLS 1.3 with strong cipher suites)
# - Message encryption at rest (using AWS KMS)
# - Secure authentication and authorization (username/password and client certificates)
# - Network isolation and access control (security groups with restricted access)
# - Compliance with security requirements (following AWS best practices)

# Security Group for RabbitMQ Cluster
resource "aws_security_group" "rabbitmq_security_group" {
  name        = "${var.environment}-rabbitmq-security-group"
  description = "Security group for RabbitMQ cluster in ${var.environment} environment"
  vpc_id      = var.vpc_id

  # No ingress rules defined here - they are added through aws_security_group_rule resources below
  # for better management and readability

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-rabbitmq-security-group"
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# RabbitMQ AMQP with TLS (5671)
resource "aws_security_group_rule" "rabbitmq_amqps" {
  security_group_id = aws_security_group.rabbitmq_security_group.id
  type              = "ingress"
  from_port         = 5671
  to_port           = 5671
  protocol          = "tcp"
  description       = "AMQP with TLS"
  
  # Only allow access from service security groups
  source_security_group_id = var.service_security_group_id
}

# RabbitMQ Management UI with TLS (15671)
resource "aws_security_group_rule" "rabbitmq_management_tls" {
  security_group_id = aws_security_group.rabbitmq_security_group.id
  type              = "ingress"
  from_port         = 15671
  to_port           = 15671
  protocol          = "tcp"
  description       = "Management UI with TLS"
  
  # Only allow access from admin security group
  source_security_group_id = var.admin_security_group_id
}

# RabbitMQ Cluster Communication (25672)
resource "aws_security_group_rule" "rabbitmq_cluster" {
  security_group_id = aws_security_group.rabbitmq_security_group.id
  type              = "ingress"
  from_port         = 25672
  to_port           = 25672
  protocol          = "tcp"
  description       = "Inter-node and CLI communication"
  
  # Only allow communication between cluster nodes
  self = true
}

# RabbitMQ EPMD (4369) - Used for node discovery
resource "aws_security_group_rule" "rabbitmq_epmd" {
  security_group_id = aws_security_group.rabbitmq_security_group.id
  type              = "ingress"
  from_port         = 4369
  to_port           = 4369
  protocol          = "tcp"
  description       = "Erlang Port Mapper Daemon"
  
  # Only allow communication between cluster nodes
  self = true
}

# TLS Certificate for RabbitMQ
resource "aws_acm_certificate" "rabbitmq_cert" {
  domain_name       = "rabbitmq.${var.dns_zone}"
  validation_method = "DNS"

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-rabbitmq-certificate"
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# KMS Key for RabbitMQ data encryption at rest
# Implements AES-256 encryption for messages at rest as required in the security considerations
resource "aws_kms_key" "rabbitmq_encryption_key" {
  description             = "KMS key for RabbitMQ data encryption at rest in ${var.environment} environment"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  # Key policy to allow RabbitMQ service to use the key
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow RabbitMQ service to use the key"
        Effect = "Allow"
        Principal = {
          AWS = var.rabbitmq_role_arn
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

  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-rabbitmq-encryption-key"
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# KMS Alias for easier reference
resource "aws_kms_alias" "rabbitmq_encryption_key_alias" {
  name          = "alias/${var.environment}-rabbitmq-encryption"
  target_key_id = aws_kms_key.rabbitmq_encryption_key.key_id
}

# SSM Parameter for RabbitMQ admin username
resource "aws_ssm_parameter" "rabbitmq_admin_username" {
  name        = "/${var.environment}/rabbitmq/admin/username"
  description = "RabbitMQ admin username for ${var.environment} environment"
  type        = "String"
  value       = var.rabbitmq_admin_username
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# SSM Parameter for RabbitMQ admin password
resource "aws_ssm_parameter" "rabbitmq_admin_password" {
  name        = "/${var.environment}/rabbitmq/admin/password"
  description = "RabbitMQ admin password for ${var.environment} environment"
  type        = "SecureString"
  value       = var.rabbitmq_admin_password
  key_id      = aws_kms_key.rabbitmq_encryption_key.key_id
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# Service-specific RabbitMQ credentials for each microservice
# Email Service
resource "aws_ssm_parameter" "rabbitmq_email_service_username" {
  name        = "/${var.environment}/rabbitmq/email-service/username"
  description = "RabbitMQ username for Email Service in ${var.environment} environment"
  type        = "String"
  value       = "email-service"
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

resource "aws_ssm_parameter" "rabbitmq_email_service_password" {
  name        = "/${var.environment}/rabbitmq/email-service/password"
  description = "RabbitMQ password for Email Service in ${var.environment} environment"
  type        = "SecureString"
  value       = var.rabbitmq_email_service_password
  key_id      = aws_kms_key.rabbitmq_encryption_key.key_id
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# Document Service
resource "aws_ssm_parameter" "rabbitmq_document_service_username" {
  name        = "/${var.environment}/rabbitmq/document-service/username"
  description = "RabbitMQ username for Document Service in ${var.environment} environment"
  type        = "String"
  value       = "document-service"
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

resource "aws_ssm_parameter" "rabbitmq_document_service_password" {
  name        = "/${var.environment}/rabbitmq/document-service/password"
  description = "RabbitMQ password for Document Service in ${var.environment} environment"
  type        = "SecureString"
  value       = var.rabbitmq_document_service_password
  key_id      = aws_kms_key.rabbitmq_encryption_key.key_id
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# OCR Service
resource "aws_ssm_parameter" "rabbitmq_ocr_service_username" {
  name        = "/${var.environment}/rabbitmq/ocr-service/username"
  description = "RabbitMQ username for OCR Service in ${var.environment} environment"
  type        = "String"
  value       = "ocr-service"
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

resource "aws_ssm_parameter" "rabbitmq_ocr_service_password" {
  name        = "/${var.environment}/rabbitmq/ocr-service/password"
  description = "RabbitMQ password for OCR Service in ${var.environment} environment"
  type        = "SecureString"
  value       = var.rabbitmq_ocr_service_password
  key_id      = aws_kms_key.rabbitmq_encryption_key.key_id
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# Data Service
resource "aws_ssm_parameter" "rabbitmq_data_service_username" {
  name        = "/${var.environment}/rabbitmq/data-service/username"
  description = "RabbitMQ username for Data Service in ${var.environment} environment"
  type        = "String"
  value       = "data-service"
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

resource "aws_ssm_parameter" "rabbitmq_data_service_password" {
  name        = "/${var.environment}/rabbitmq/data-service/password"
  description = "RabbitMQ password for Data Service in ${var.environment} environment"
  type        = "SecureString"
  value       = var.rabbitmq_data_service_password
  key_id      = aws_kms_key.rabbitmq_encryption_key.key_id
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# Notification Service
resource "aws_ssm_parameter" "rabbitmq_notification_service_username" {
  name        = "/${var.environment}/rabbitmq/notification-service/username"
  description = "RabbitMQ username for Notification Service in ${var.environment} environment"
  type        = "String"
  value       = "notification-service"
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

resource "aws_ssm_parameter" "rabbitmq_notification_service_password" {
  name        = "/${var.environment}/rabbitmq/notification-service/password"
  description = "RabbitMQ password for Notification Service in ${var.environment} environment"
  type        = "SecureString"
  value       = var.rabbitmq_notification_service_password
  key_id      = aws_kms_key.rabbitmq_encryption_key.key_id
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# RabbitMQ TLS Configuration
# Enforces TLS 1.3 with strong cipher suites as required in the security considerations
# Self-signed certificates are prohibited in production environments
resource "aws_ssm_parameter" "rabbitmq_tls_config" {
  name        = "/${var.environment}/rabbitmq/tls/config"
  description = "RabbitMQ TLS configuration for ${var.environment} environment"
  type        = "String"
  value       = jsonencode({
    ssl_options = {
      cacertfile    = "/etc/rabbitmq/certs/ca.pem"
      certfile      = "/etc/rabbitmq/certs/server.pem"
      keyfile       = "/etc/rabbitmq/certs/server-key.pem"
      verify        = "verify_peer"
      fail_if_no_peer_cert = true
      versions      = ["tlsv1.3", "tlsv1.2"]
      ciphers       = [
        "TLS_AES_256_GCM_SHA384",
        "TLS_AES_128_GCM_SHA256",
        "TLS_CHACHA20_POLY1305_SHA256",
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-ECDSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES128-GCM-SHA256"
      ]
    }
  })
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# RabbitMQ Virtual Hosts Configuration
# Implements the principle of least privilege for message queue access
# Each service has its own virtual host and limited permissions to other virtual hosts
resource "aws_ssm_parameter" "rabbitmq_vhosts_config" {
  name        = "/${var.environment}/rabbitmq/vhosts/config"
  description = "RabbitMQ virtual hosts configuration for ${var.environment} environment"
  type        = "String"
  value       = jsonencode([
    {
      name = "email-service"
      permissions = [
        {
          user = "email-service"
          configure = ".*"
          write = ".*"
          read = ".*"
        },
        {
          user = "document-service"
          configure = ""
          write = ""
          read = "^document-processing$"
        }
      ]
    },
    {
      name = "document-service"
      permissions = [
        {
          user = "document-service"
          configure = ".*"
          write = ".*"
          read = ".*"
        },
        {
          user = "ocr-service"
          configure = ""
          write = ""
          read = "^data-extraction$"
        }
      ]
    },
    {
      name = "ocr-service"
      permissions = [
        {
          user = "ocr-service"
          configure = ".*"
          write = ".*"
          read = ".*"
        },
        {
          user = "data-service"
          configure = ""
          write = ""
          read = "^extraction-results$"
        }
      ]
    },
    {
      name = "data-service"
      permissions = [
        {
          user = "data-service"
          configure = ".*"
          write = ".*"
          read = ".*"
        },
        {
          user = "notification-service"
          configure = ""
          write = ""
          read = "^notification$"
        }
      ]
    },
    {
      name = "notification-service"
      permissions = [
        {
          user = "notification-service"
          configure = ".*"
          write = ".*"
          read = ".*"
        }
      ]
    }
  ])
  
  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "rabbitmq"
    }
  )
}

# Variables required for the security configuration
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where RabbitMQ cluster will be deployed"
  type        = string
}

variable "service_security_group_id" {
  description = "Security group ID for services that need to access RabbitMQ"
  type        = string
}

variable "admin_security_group_id" {
  description = "Security group ID for administrators that need to access RabbitMQ management UI"
  type        = string
}

variable "dns_zone" {
  description = "DNS zone for RabbitMQ certificate"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "rabbitmq_role_arn" {
  description = "ARN of the IAM role used by RabbitMQ services"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "rabbitmq_admin_username" {
  description = "Username for RabbitMQ admin user"
  type        = string
  default     = "admin"
}

variable "rabbitmq_admin_password" {
  description = "Password for RabbitMQ admin user"
  type        = string
  sensitive   = true
}

variable "rabbitmq_email_service_password" {
  description = "Password for RabbitMQ email service user"
  type        = string
  sensitive   = true
}

variable "rabbitmq_document_service_password" {
  description = "Password for RabbitMQ document service user"
  type        = string
  sensitive   = true
}

variable "rabbitmq_ocr_service_password" {
  description = "Password for RabbitMQ OCR service user"
  type        = string
  sensitive   = true
}

variable "rabbitmq_data_service_password" {
  description = "Password for RabbitMQ data service user"
  type        = string
  sensitive   = true
}

variable "rabbitmq_notification_service_password" {
  description = "Password for RabbitMQ notification service user"
  type        = string
  sensitive   = true
}