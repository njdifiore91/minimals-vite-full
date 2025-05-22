# Main Terraform Configuration for RabbitMQ Messaging Infrastructure
#
# This file serves as the entry point for the RabbitMQ messaging module.
# It defines the main RabbitMQ infrastructure with 3 nodes, disk-based persistence,
# quorum queues, and high availability settings.

# Local variables for environment-specific settings
locals {
  # Environment-specific instance types
  instance_types = {
    development = "mq.m5.large"
    staging     = "mq.m5.large"
    production  = "mq.m5.xlarge"
  }
  
  # Environment-specific node counts
  node_counts = {
    development = 3
    staging     = 3
    production  = 3
  }
  
  # Environment-specific tags
  environment_tags = {
    development = {
      Environment = "development"
      CostCenter = "dev-ops"
    }
    staging = {
      Environment = "staging"
      CostCenter = "dev-ops"
    }
    production = {
      Environment = "production"
      CostCenter = "operations"
    }
  }
  
  # Merge common tags with environment-specific tags
  tags = merge(
    var.common_tags,
    local.environment_tags[var.environment],
    {
      Service     = "mca-messaging"
      ManagedBy   = "terraform"
      Application = "mca-application-processing"
    }
  )
  
  # Determine instance type based on environment
  instance_type = lookup(local.instance_types, var.environment, "mq.m5.large")
}

# AWS provider configuration
provider "aws" {
  region = var.aws_region
}

# RabbitMQ provider configuration
provider "rabbitmq" {
  endpoint = "https://${aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0}:15671"
  username = var.rabbitmq_admin_username
  password = var.rabbitmq_admin_password
}

# Security group for RabbitMQ cluster
resource "aws_security_group" "rabbitmq" {
  name        = "${var.environment}-mca-rabbitmq-sg"
  description = "Security group for RabbitMQ cluster"
  vpc_id      = var.vpc_id
  
  # AMQP protocol
  ingress {
    from_port   = 5671
    to_port     = 5671
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "AMQP with TLS"
  }
  
  # Management UI
  ingress {
    from_port   = 15671
    to_port     = 15671
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Management UI with TLS"
  }
  
  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  # Apply tags
  tags = local.tags
}

# Create CloudWatch log group for RabbitMQ logs
resource "aws_cloudwatch_log_group" "rabbitmq_logs" {
  name              = "/aws/amazonmq/${var.environment}-mca-rabbitmq-cluster"
  retention_in_days = 30
  
  # Apply tags
  tags = local.tags
}

# Create KMS key for encryption
resource "aws_kms_key" "rabbitmq" {
  description             = "KMS key for RabbitMQ encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  
  # Apply tags
  tags = local.tags
}

# Create KMS key alias
resource "aws_kms_alias" "rabbitmq" {
  name          = "alias/${var.environment}-mca-rabbitmq"
  target_key_id = aws_kms_key.rabbitmq.key_id
}

# Create SNS topic for RabbitMQ alarms
resource "aws_sns_topic" "rabbitmq_alarms" {
  name = "${var.environment}-mca-rabbitmq-alarms"
  
  # Apply tags
  tags = local.tags
}

# Create IAM role for RabbitMQ
resource "aws_iam_role" "rabbitmq" {
  name = "${var.environment}-mca-rabbitmq-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "mq.amazonaws.com"
        }
      }
    ]
  })
  
  # Apply tags
  tags = local.tags
}

# Create IAM policy for RabbitMQ
resource "aws_iam_policy" "rabbitmq" {
  name        = "${var.environment}-mca-rabbitmq-policy"
  description = "Policy for RabbitMQ cluster"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "ec2:DescribeInstances",
          "ec2:DescribeSubnets",
          "ec2:DescribeVpcs",
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Attach IAM policy to IAM role
resource "aws_iam_role_policy_attachment" "rabbitmq" {
  role       = aws_iam_role.rabbitmq.name
  policy_arn = aws_iam_policy.rabbitmq.arn
}

# Define additional variables needed for the module
variable "vpc_id" {
  description = "VPC ID for RabbitMQ deployment"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access RabbitMQ"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}