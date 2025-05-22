# =============================================================================
# Terraform Outputs for MCA Application Processing System
# =============================================================================
# This file defines all outputs from the Terraform configuration, including:
# - Database connection strings
# - Messaging endpoints
# - Cache addresses
# - Storage bucket information
# - Kubernetes cluster information
# These outputs are used by application services to connect to the provisioned
# infrastructure and are essential for CI/CD pipeline integration.
# =============================================================================

# -----------------------------------------------------------------------------
# PostgreSQL Database Outputs
# -----------------------------------------------------------------------------

output "postgres_host" {
  description = "PostgreSQL server hostname"
  value       = module.database.postgres_host
}

output "postgres_port" {
  description = "PostgreSQL server port"
  value       = module.database.postgres_port
}

output "postgres_database_name" {
  description = "PostgreSQL database name"
  value       = module.database.postgres_database_name
}

output "postgres_username" {
  description = "PostgreSQL admin username"
  value       = module.database.postgres_username
  sensitive   = true
}

output "postgres_password" {
  description = "PostgreSQL admin password"
  value       = module.database.postgres_password
  sensitive   = true
}

output "postgres_connection_string" {
  description = "PostgreSQL connection string"
  value       = module.database.postgres_connection_string
  sensitive   = true
}

output "postgres_read_replicas" {
  description = "List of PostgreSQL read replica endpoints"
  value       = module.database.postgres_read_replicas
}

# -----------------------------------------------------------------------------
# RabbitMQ Messaging Outputs
# -----------------------------------------------------------------------------

output "rabbitmq_host" {
  description = "RabbitMQ server hostname"
  value       = module.messaging.rabbitmq_host
}

output "rabbitmq_port" {
  description = "RabbitMQ server port"
  value       = module.messaging.rabbitmq_port
}

output "rabbitmq_username" {
  description = "RabbitMQ admin username"
  value       = module.messaging.rabbitmq_username
  sensitive   = true
}

output "rabbitmq_password" {
  description = "RabbitMQ admin password"
  value       = module.messaging.rabbitmq_password
  sensitive   = true
}

output "rabbitmq_connection_string" {
  description = "RabbitMQ connection string"
  value       = module.messaging.rabbitmq_connection_string
  sensitive   = true
}

output "rabbitmq_management_url" {
  description = "RabbitMQ management interface URL"
  value       = module.messaging.rabbitmq_management_url
}

output "rabbitmq_vhost" {
  description = "RabbitMQ virtual host for application"
  value       = module.messaging.rabbitmq_vhost
}

# -----------------------------------------------------------------------------
# Redis Cache Outputs
# -----------------------------------------------------------------------------

output "redis_host" {
  description = "Redis server hostname"
  value       = module.cache.redis_host
}

output "redis_port" {
  description = "Redis server port"
  value       = module.cache.redis_port
}

output "redis_password" {
  description = "Redis server password"
  value       = module.cache.redis_password
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = module.cache.redis_connection_string
  sensitive   = true
}

output "redis_cache_instance" {
  description = "Redis instance for application data caching (15 min TTL)"
  value       = module.cache.redis_cache_instance
}

output "redis_session_instance" {
  description = "Redis instance for session management (24h TTL)"
  value       = module.cache.redis_session_instance
}

# -----------------------------------------------------------------------------
# S3-Compatible Storage Outputs
# -----------------------------------------------------------------------------

output "s3_bucket_name" {
  description = "S3 bucket name for document storage"
  value       = module.storage.s3_bucket_name
}

output "s3_bucket_region" {
  description = "S3 bucket region"
  value       = module.storage.s3_bucket_region
}

output "s3_endpoint" {
  description = "S3-compatible storage endpoint"
  value       = module.storage.s3_endpoint
}

output "s3_access_key" {
  description = "S3 access key for document storage"
  value       = module.storage.s3_access_key
  sensitive   = true
}

output "s3_secret_key" {
  description = "S3 secret key for document storage"
  value       = module.storage.s3_secret_key
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Kubernetes Cluster Outputs
# -----------------------------------------------------------------------------

output "kubernetes_cluster_name" {
  description = "Name of the Kubernetes cluster"
  value       = module.kubernetes.cluster_name
}

output "kubernetes_cluster_endpoint" {
  description = "Endpoint for Kubernetes API server"
  value       = module.kubernetes.cluster_endpoint
}

output "kubernetes_cluster_ca_certificate" {
  description = "CA certificate for Kubernetes cluster"
  value       = module.kubernetes.cluster_ca_certificate
  sensitive   = true
}

output "kubernetes_config_context" {
  description = "Kubernetes config context name"
  value       = module.kubernetes.config_context
}

# -----------------------------------------------------------------------------
# Network Outputs
# -----------------------------------------------------------------------------

output "vpc_id" {
  description = "ID of the VPC where resources are deployed"
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.network.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.network.public_subnet_ids
}

# -----------------------------------------------------------------------------
# API Gateway Outputs
# -----------------------------------------------------------------------------

output "api_gateway_url" {
  description = "URL for the Kong API Gateway"
  value       = module.api_gateway.api_gateway_url
}

output "api_gateway_admin_url" {
  description = "Admin URL for the Kong API Gateway"
  value       = module.api_gateway.api_gateway_admin_url
}

# -----------------------------------------------------------------------------
# Environment Information
# -----------------------------------------------------------------------------

output "environment" {
  description = "Deployment environment (development, staging, production)"
  value       = var.environment
}

output "region" {
  description = "AWS/Azure/GCP region where resources are deployed"
  value       = var.region
}

# -----------------------------------------------------------------------------
# CI/CD Integration Outputs
# -----------------------------------------------------------------------------

output "ci_cd_role_arn" {
  description = "ARN of the IAM role for CI/CD pipeline"
  value       = module.security.ci_cd_role_arn
}

output "ecr_repository_url" {
  description = "URL of the ECR repository for container images"
  value       = module.container_registry.repository_url
}

# -----------------------------------------------------------------------------
# Monitoring Outputs
# -----------------------------------------------------------------------------

output "monitoring_dashboard_url" {
  description = "URL for the monitoring dashboard"
  value       = module.monitoring.dashboard_url
}

output "logging_endpoint" {
  description = "Endpoint for centralized logging"
  value       = module.monitoring.logging_endpoint
}

# -----------------------------------------------------------------------------
# Composite Outputs for Application Services
# -----------------------------------------------------------------------------

output "email_service_config" {
  description = "Configuration for Email Service"
  value = {
    rabbitmq_host     = module.messaging.rabbitmq_host
    rabbitmq_port     = module.messaging.rabbitmq_port
    rabbitmq_username = module.messaging.rabbitmq_username
    rabbitmq_vhost    = module.messaging.rabbitmq_vhost
    s3_bucket_name    = module.storage.s3_bucket_name
    s3_endpoint       = module.storage.s3_endpoint
  }
  sensitive = true
}

output "document_service_config" {
  description = "Configuration for Document Service"
  value = {
    rabbitmq_host     = module.messaging.rabbitmq_host
    rabbitmq_port     = module.messaging.rabbitmq_port
    rabbitmq_username = module.messaging.rabbitmq_username
    rabbitmq_vhost    = module.messaging.rabbitmq_vhost
    s3_bucket_name    = module.storage.s3_bucket_name
    s3_endpoint       = module.storage.s3_endpoint
    redis_host        = module.cache.redis_host
    redis_port        = module.cache.redis_port
  }
  sensitive = true
}

output "ocr_service_config" {
  description = "Configuration for OCR Service"
  value = {
    rabbitmq_host     = module.messaging.rabbitmq_host
    rabbitmq_port     = module.messaging.rabbitmq_port
    rabbitmq_username = module.messaging.rabbitmq_username
    rabbitmq_vhost    = module.messaging.rabbitmq_vhost
    s3_bucket_name    = module.storage.s3_bucket_name
    s3_endpoint       = module.storage.s3_endpoint
    redis_host        = module.cache.redis_host
    redis_port        = module.cache.redis_port
  }
  sensitive = true
}

output "data_service_config" {
  description = "Configuration for Data Service"
  value = {
    postgres_host        = module.database.postgres_host
    postgres_port        = module.database.postgres_port
    postgres_database    = module.database.postgres_database_name
    postgres_username    = module.database.postgres_username
    rabbitmq_host        = module.messaging.rabbitmq_host
    rabbitmq_port        = module.messaging.rabbitmq_port
    rabbitmq_username    = module.messaging.rabbitmq_username
    rabbitmq_vhost       = module.messaging.rabbitmq_vhost
    redis_host           = module.cache.redis_host
    redis_port           = module.cache.redis_port
    s3_bucket_name       = module.storage.s3_bucket_name
    s3_endpoint          = module.storage.s3_endpoint
  }
  sensitive = true
}

output "notification_service_config" {
  description = "Configuration for Notification Service"
  value = {
    rabbitmq_host     = module.messaging.rabbitmq_host
    rabbitmq_port     = module.messaging.rabbitmq_port
    rabbitmq_username = module.messaging.rabbitmq_username
    rabbitmq_vhost    = module.messaging.rabbitmq_vhost
    redis_host        = module.cache.redis_host
    redis_port        = module.cache.redis_port
  }
  sensitive = true
}

output "frontend_config" {
  description = "Configuration for Frontend Application"
  value = {
    api_gateway_url = module.api_gateway.api_gateway_url
  }
}