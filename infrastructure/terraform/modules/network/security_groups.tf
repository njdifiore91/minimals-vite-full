# Security Groups for MCA Application Processing System
# This file defines security groups for different service types with appropriate ingress and egress rules
# to enforce proper access patterns between services and protect against unauthorized access.

# Variables for common ports
locals {
  http_port         = 80
  https_port        = 443
  postgres_port     = 5432
  rabbitmq_port     = 5672
  rabbitmq_mgmt_port = 15672
  redis_port        = 6379
  api_gateway_port  = 8000
  api_gateway_admin_port = 8001
  email_service_port = 3000
  document_service_port = 3001
  ocr_service_port  = 3002
  data_service_port = 8080
  notification_service_port = 3003
}

# Frontend Security Group
# Allows HTTP/HTTPS ingress from public internet and egress to API Gateway
resource "aws_security_group" "frontend" {
  name        = "${var.environment}-frontend-sg"
  description = "Security group for frontend services"
  vpc_id      = var.vpc_id

  # Allow HTTP from anywhere (will be redirected to HTTPS)
  ingress {
    from_port   = local.http_port
    to_port     = local.http_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP access from anywhere"
  }

  # Allow HTTPS from anywhere
  ingress {
    from_port   = local.https_port
    to_port     = local.https_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS access from anywhere"
  }

  # Egress to API Gateway only
  egress {
    from_port       = local.api_gateway_port
    to_port         = local.api_gateway_port
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "Allow outbound traffic to API Gateway"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-frontend-sg"
      Service = "Frontend"
    }
  )
}

# API Gateway Security Group
# Acts as the primary security boundary for external requests
resource "aws_security_group" "api_gateway" {
  name        = "${var.environment}-api-gateway-sg"
  description = "Security group for API Gateway"
  vpc_id      = var.vpc_id

  # Allow HTTPS from frontend
  ingress {
    from_port       = local.api_gateway_port
    to_port         = local.api_gateway_port
    protocol        = "tcp"
    security_groups = [aws_security_group.frontend.id]
    description     = "Allow API access from frontend"
  }

  # Allow admin port access from internal networks only
  ingress {
    from_port   = local.api_gateway_admin_port
    to_port     = local.api_gateway_admin_port
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Allow admin access from internal network only"
  }

  # Egress to microservices
  egress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [
      aws_security_group.microservices.id,
      aws_security_group.data_service.id
    ]
    description     = "Allow outbound traffic to microservices"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-api-gateway-sg"
      Service = "API Gateway"
    }
  )
}

# General Microservices Security Group
# Base security group for all microservices with common rules
resource "aws_security_group" "microservices" {
  name        = "${var.environment}-microservices-sg"
  description = "Base security group for all microservices"
  vpc_id      = var.vpc_id

  # Allow traffic from API Gateway
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "Allow traffic from API Gateway"
  }

  # Allow internal service communication
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    self            = true
    description     = "Allow internal service communication"
  }

  # Egress to RabbitMQ
  egress {
    from_port       = local.rabbitmq_port
    to_port         = local.rabbitmq_port
    protocol        = "tcp"
    security_groups = [aws_security_group.rabbitmq.id]
    description     = "Allow outbound traffic to RabbitMQ"
  }

  # Egress to Redis
  egress {
    from_port       = local.redis_port
    to_port         = local.redis_port
    protocol        = "tcp"
    security_groups = [aws_security_group.redis.id]
    description     = "Allow outbound traffic to Redis"
  }

  # Egress to PostgreSQL
  egress {
    from_port       = local.postgres_port
    to_port         = local.postgres_port
    protocol        = "tcp"
    security_groups = [aws_security_group.postgres.id]
    description     = "Allow outbound traffic to PostgreSQL"
  }

  # Egress to S3 via VPC endpoint
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    prefix_list_ids = [var.s3_prefix_list_id]
    description = "Allow outbound traffic to S3 via VPC endpoint"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-microservices-sg"
      Service = "Microservices"
    }
  )
}

# Email Service Security Group
# Specific rules for the email monitoring service
resource "aws_security_group" "email_service" {
  name        = "${var.environment}-email-service-sg"
  description = "Security group for Email Service"
  vpc_id      = var.vpc_id

  # Allow traffic from API Gateway
  ingress {
    from_port       = local.email_service_port
    to_port         = local.email_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "Allow traffic from API Gateway"
  }

  # Egress to IMAPS (IMAP over TLS/SSL)
  egress {
    from_port   = 993
    to_port     = 993
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound traffic to IMAPS"
  }

  # Egress to RabbitMQ
  egress {
    from_port       = local.rabbitmq_port
    to_port         = local.rabbitmq_port
    protocol        = "tcp"
    security_groups = [aws_security_group.rabbitmq.id]
    description     = "Allow outbound traffic to RabbitMQ"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-email-service-sg"
      Service = "Email Service"
    }
  )
}

# Document Service Security Group
# Specific rules for the document classification service
resource "aws_security_group" "document_service" {
  name        = "${var.environment}-document-service-sg"
  description = "Security group for Document Service"
  vpc_id      = var.vpc_id

  # Allow traffic from API Gateway
  ingress {
    from_port       = local.document_service_port
    to_port         = local.document_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "Allow traffic from API Gateway"
  }

  # Allow traffic from RabbitMQ consumers
  ingress {
    from_port       = local.document_service_port
    to_port         = local.document_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.microservices.id]
    description     = "Allow traffic from other microservices"
  }

  # Egress to S3 via VPC endpoint
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    prefix_list_ids = [var.s3_prefix_list_id]
    description = "Allow outbound traffic to S3 via VPC endpoint"
  }

  # Egress to RabbitMQ
  egress {
    from_port       = local.rabbitmq_port
    to_port         = local.rabbitmq_port
    protocol        = "tcp"
    security_groups = [aws_security_group.rabbitmq.id]
    description     = "Allow outbound traffic to RabbitMQ"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-document-service-sg"
      Service = "Document Service"
    }
  )
}

# OCR Service Security Group
# Specific rules for the OCR extraction service
resource "aws_security_group" "ocr_service" {
  name        = "${var.environment}-ocr-service-sg"
  description = "Security group for OCR Service"
  vpc_id      = var.vpc_id

  # Allow traffic from API Gateway
  ingress {
    from_port       = local.ocr_service_port
    to_port         = local.ocr_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "Allow traffic from API Gateway"
  }

  # Allow traffic from RabbitMQ consumers
  ingress {
    from_port       = local.ocr_service_port
    to_port         = local.ocr_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.microservices.id]
    description     = "Allow traffic from other microservices"
  }

  # Egress to S3 via VPC endpoint
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    prefix_list_ids = [var.s3_prefix_list_id]
    description = "Allow outbound traffic to S3 via VPC endpoint"
  }

  # Egress to RabbitMQ
  egress {
    from_port       = local.rabbitmq_port
    to_port         = local.rabbitmq_port
    protocol        = "tcp"
    security_groups = [aws_security_group.rabbitmq.id]
    description     = "Allow outbound traffic to RabbitMQ"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-ocr-service-sg"
      Service = "OCR Service"
    }
  )
}

# Data Service Security Group
# Specific rules for the core data management service
resource "aws_security_group" "data_service" {
  name        = "${var.environment}-data-service-sg"
  description = "Security group for Data Service"
  vpc_id      = var.vpc_id

  # Allow traffic from API Gateway
  ingress {
    from_port       = local.data_service_port
    to_port         = local.data_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "Allow traffic from API Gateway"
  }

  # Allow traffic from RabbitMQ consumers
  ingress {
    from_port       = local.data_service_port
    to_port         = local.data_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.microservices.id]
    description     = "Allow traffic from other microservices"
  }

  # Egress to PostgreSQL
  egress {
    from_port       = local.postgres_port
    to_port         = local.postgres_port
    protocol        = "tcp"
    security_groups = [aws_security_group.postgres.id]
    description     = "Allow outbound traffic to PostgreSQL"
  }

  # Egress to Redis
  egress {
    from_port       = local.redis_port
    to_port         = local.redis_port
    protocol        = "tcp"
    security_groups = [aws_security_group.redis.id]
    description     = "Allow outbound traffic to Redis"
  }

  # Egress to RabbitMQ
  egress {
    from_port       = local.rabbitmq_port
    to_port         = local.rabbitmq_port
    protocol        = "tcp"
    security_groups = [aws_security_group.rabbitmq.id]
    description     = "Allow outbound traffic to RabbitMQ"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-data-service-sg"
      Service = "Data Service"
    }
  )
}

# Notification Service Security Group
# Specific rules for the notification and webhook service
resource "aws_security_group" "notification_service" {
  name        = "${var.environment}-notification-service-sg"
  description = "Security group for Notification Service"
  vpc_id      = var.vpc_id

  # Allow traffic from API Gateway
  ingress {
    from_port       = local.notification_service_port
    to_port         = local.notification_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.api_gateway.id]
    description     = "Allow traffic from API Gateway"
  }

  # Allow traffic from RabbitMQ consumers
  ingress {
    from_port       = local.notification_service_port
    to_port         = local.notification_service_port
    protocol        = "tcp"
    security_groups = [aws_security_group.microservices.id]
    description     = "Allow traffic from other microservices"
  }

  # Egress to external webhook endpoints
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound traffic to external webhook endpoints"
  }

  # Egress to RabbitMQ
  egress {
    from_port       = local.rabbitmq_port
    to_port         = local.rabbitmq_port
    protocol        = "tcp"
    security_groups = [aws_security_group.rabbitmq.id]
    description     = "Allow outbound traffic to RabbitMQ"
  }

  # Egress to Redis for rate limiting and caching
  egress {
    from_port       = local.redis_port
    to_port         = local.redis_port
    protocol        = "tcp"
    security_groups = [aws_security_group.redis.id]
    description     = "Allow outbound traffic to Redis"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-notification-service-sg"
      Service = "Notification Service"
    }
  )
}

# PostgreSQL Security Group
# Restricted access to database instances
resource "aws_security_group" "postgres" {
  name        = "${var.environment}-postgres-sg"
  description = "Security group for PostgreSQL database"
  vpc_id      = var.vpc_id

  # Allow PostgreSQL traffic from Data Service
  ingress {
    from_port       = local.postgres_port
    to_port         = local.postgres_port
    protocol        = "tcp"
    security_groups = [aws_security_group.data_service.id]
    description     = "Allow PostgreSQL traffic from Data Service"
  }

  # Allow PostgreSQL traffic from Microservices (if needed)
  ingress {
    from_port       = local.postgres_port
    to_port         = local.postgres_port
    protocol        = "tcp"
    security_groups = [aws_security_group.microservices.id]
    description     = "Allow PostgreSQL traffic from Microservices"
  }

  # No direct outbound access needed for database
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow minimal outbound traffic for updates and patches"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-postgres-sg"
      Service = "PostgreSQL"
    }
  )
}

# RabbitMQ Security Group
# Secure messaging configuration
resource "aws_security_group" "rabbitmq" {
  name        = "${var.environment}-rabbitmq-sg"
  description = "Security group for RabbitMQ messaging"
  vpc_id      = var.vpc_id

  # Allow AMQP traffic from Microservices
  ingress {
    from_port       = local.rabbitmq_port
    to_port         = local.rabbitmq_port
    protocol        = "tcp"
    security_groups = [
      aws_security_group.microservices.id,
      aws_security_group.email_service.id,
      aws_security_group.document_service.id,
      aws_security_group.ocr_service.id,
      aws_security_group.data_service.id,
      aws_security_group.notification_service.id
    ]
    description     = "Allow AMQP traffic from services"
  }

  # Allow management interface from internal networks only
  ingress {
    from_port   = local.rabbitmq_mgmt_port
    to_port     = local.rabbitmq_mgmt_port
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Allow management interface from internal network only"
  }

  # Minimal outbound access for cluster communication and updates
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound traffic for cluster communication and updates"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-rabbitmq-sg"
      Service = "RabbitMQ"
    }
  )
}

# Redis Security Group
# Restricted access to Redis cache instances
resource "aws_security_group" "redis" {
  name        = "${var.environment}-redis-sg"
  description = "Security group for Redis cache"
  vpc_id      = var.vpc_id

  # Allow Redis traffic from services that need caching
  ingress {
    from_port       = local.redis_port
    to_port         = local.redis_port
    protocol        = "tcp"
    security_groups = [
      aws_security_group.microservices.id,
      aws_security_group.data_service.id,
      aws_security_group.notification_service.id
    ]
    description     = "Allow Redis traffic from services"
  }

  # No direct outbound access needed for Redis
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow minimal outbound traffic for cluster communication"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-redis-sg"
      Service = "Redis"
    }
  )
}

# Variables expected to be passed to this module
variable "environment" {
  description = "Environment name (e.g., dev, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where security groups will be created"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC for internal network rules"
  type        = string
}

variable "s3_prefix_list_id" {
  description = "Prefix list ID for S3 VPC endpoint"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Outputs
output "frontend_sg_id" {
  description = "ID of the frontend security group"
  value       = aws_security_group.frontend.id
}

output "api_gateway_sg_id" {
  description = "ID of the API Gateway security group"
  value       = aws_security_group.api_gateway.id
}

output "microservices_sg_id" {
  description = "ID of the base microservices security group"
  value       = aws_security_group.microservices.id
}

output "email_service_sg_id" {
  description = "ID of the Email Service security group"
  value       = aws_security_group.email_service.id
}

output "document_service_sg_id" {
  description = "ID of the Document Service security group"
  value       = aws_security_group.document_service.id
}

output "ocr_service_sg_id" {
  description = "ID of the OCR Service security group"
  value       = aws_security_group.ocr_service.id
}

output "data_service_sg_id" {
  description = "ID of the Data Service security group"
  value       = aws_security_group.data_service.id
}

output "notification_service_sg_id" {
  description = "ID of the Notification Service security group"
  value       = aws_security_group.notification_service.id
}

output "postgres_sg_id" {
  description = "ID of the PostgreSQL security group"
  value       = aws_security_group.postgres.id
}

output "rabbitmq_sg_id" {
  description = "ID of the RabbitMQ security group"
  value       = aws_security_group.rabbitmq.id
}

output "redis_sg_id" {
  description = "ID of the Redis security group"
  value       = aws_security_group.redis.id
}