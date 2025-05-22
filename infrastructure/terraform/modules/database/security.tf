# PostgreSQL Database Security Configuration
# This file implements comprehensive security measures for PostgreSQL databases
# including encryption, network security, and authentication controls.

# KMS Key for database encryption at rest with AES-256
resource "aws_kms_key" "postgres_encryption_key" {
  description             = "KMS key for PostgreSQL database encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  key_usage               = "ENCRYPT_DECRYPT"
  
  # Enable automatic key rotation every 90 days
  rotation_period = "7776000s" # 90 days in seconds
  
  # Key policy to allow RDS service to use the key
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "Enable IAM User Permissions",
        Effect = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action   = "kms:*",
        Resource = "*"
      },
      {
        Sid    = "Allow RDS Service to use the key",
        Effect = "Allow",
        Principal = {
          Service = "rds.amazonaws.com"
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
  
  tags = {
    Name        = "postgres-encryption-key"
    Environment = var.environment
    Managed_by  = "terraform"
  }
}

# KMS Alias for easier reference
resource "aws_kms_alias" "postgres_encryption_key_alias" {
  name          = "alias/postgres-encryption-key-${var.environment}"
  target_key_id = aws_kms_key.postgres_encryption_key.key_id
}

# Security Group for PostgreSQL database instances
resource "aws_security_group" "postgres_sg" {
  name        = "postgres-security-group-${var.environment}"
  description = "Security group for PostgreSQL database instances"
  vpc_id      = var.vpc_id
  
  tags = {
    Name        = "postgres-sg-${var.environment}"
    Environment = var.environment
    Managed_by  = "terraform"
  }
}

# Ingress rule for PostgreSQL port (5432) - restricted to application subnets only
resource "aws_security_group_rule" "postgres_ingress" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.postgres_sg.id
  source_security_group_id = var.app_security_group_id
  description              = "Allow PostgreSQL traffic from application servers"
}

# Egress rule - allow all outbound traffic
resource "aws_security_group_rule" "postgres_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.postgres_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all outbound traffic"
}

# Parameter group to enforce SSL/TLS connections
resource "aws_db_parameter_group" "postgres_param_group" {
  name        = "postgres-params-${var.environment}"
  family      = "postgres14"
  description = "PostgreSQL parameter group with enhanced security settings"
  
  parameter {
    name  = "rds.force_ssl"
    value = "1"
    apply_method = "pending-reboot"
  }
  
  parameter {
    name  = "ssl"
    value = "1"
    apply_method = "pending-reboot"
  }
  
  # Configure strong TLS cipher suites
  parameter {
    name  = "ssl_ciphers"
    value = "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256"
    apply_method = "pending-reboot"
  }
  
  tags = {
    Name        = "postgres-params-${var.environment}"
    Environment = var.environment
    Managed_by  = "terraform"
  }
}

# IAM Role for RDS IAM Authentication
resource "aws_iam_role" "rds_iam_auth_role" {
  name = "rds-iam-auth-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "rds.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "rds-iam-auth-role-${var.environment}"
    Environment = var.environment
    Managed_by  = "terraform"
  }
}

# IAM Policy for RDS IAM Authentication
resource "aws_iam_policy" "rds_iam_auth_policy" {
  name        = "rds-iam-auth-policy-${var.environment}"
  description = "Policy for RDS IAM Authentication"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "rds-db:connect"
        ],
        Resource = "arn:aws:rds-db:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:dbuser:*/*"
      }
    ]
  })
}

# Attach the IAM policy to the role
resource "aws_iam_role_policy_attachment" "rds_iam_auth_attachment" {
  role       = aws_iam_role.rds_iam_auth_role.name
  policy_arn = aws_iam_policy.rds_iam_auth_policy.arn
}

# CloudWatch Logs for RDS audit logging
resource "aws_cloudwatch_log_group" "postgres_audit_logs" {
  name              = "/aws/rds/instance/postgres-${var.environment}/audit"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.postgres_encryption_key.arn
  
  tags = {
    Name        = "postgres-audit-logs-${var.environment}"
    Environment = var.environment
    Managed_by  = "terraform"
  }
}

# Required data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Variables
variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where the database will be deployed"
  type        = string
}

variable "app_security_group_id" {
  description = "Security group ID of the application servers that will connect to the database"
  type        = string
}

# Outputs
output "kms_key_id" {
  description = "The KMS key ID used for database encryption"
  value       = aws_kms_key.postgres_encryption_key.key_id
}

output "security_group_id" {
  description = "The ID of the security group for PostgreSQL instances"
  value       = aws_security_group.postgres_sg.id
}

output "parameter_group_name" {
  description = "The name of the parameter group for PostgreSQL instances"
  value       = aws_db_parameter_group.postgres_param_group.name
}

output "iam_role_arn" {
  description = "The ARN of the IAM role for RDS IAM authentication"
  value       = aws_iam_role.rds_iam_auth_role.arn
}