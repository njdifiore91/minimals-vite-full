# Development Environment Outputs
# This file exports essential information from the development environment as Terraform outputs,
# including connection endpoints, credentials, and resource identifiers.
# These outputs are consumed by application configuration and developers to connect to the infrastructure services.

# PostgreSQL Database Outputs
output "postgres_endpoint" {
  description = "The connection endpoint for the PostgreSQL database in development environment"
  value       = module.database.endpoint
  sensitive   = false
}

output "postgres_database_name" {
  description = "The name of the PostgreSQL database"
  value       = module.database.database_name
  sensitive   = false
}

output "postgres_port" {
  description = "The port on which the PostgreSQL database accepts connections"
  value       = module.database.port
  sensitive   = false
}

output "postgres_username" {
  description = "The username for the PostgreSQL database"
  value       = module.database.username
  sensitive   = true
}

output "postgres_password" {
  description = "The password for the PostgreSQL database"
  value       = module.database.password
  sensitive   = true
}

output "postgres_connection_string" {
  description = "The connection string for the PostgreSQL database"
  value       = module.database.connection_string
  sensitive   = true
}

# RabbitMQ Messaging Outputs
output "rabbitmq_endpoint" {
  description = "The connection endpoint for the RabbitMQ server"
  value       = module.messaging.endpoint
  sensitive   = false
}

output "rabbitmq_management_url" {
  description = "The URL for the RabbitMQ management interface"
  value       = module.messaging.management_url
  sensitive   = false
}

output "rabbitmq_port" {
  description = "The port on which the RabbitMQ server accepts connections"
  value       = module.messaging.port
  sensitive   = false
}

output "rabbitmq_vhost" {
  description = "The virtual host for the RabbitMQ server"
  value       = module.messaging.vhost
  sensitive   = false
}

output "rabbitmq_username" {
  description = "The username for the RabbitMQ server"
  value       = module.messaging.username
  sensitive   = true
}

output "rabbitmq_password" {
  description = "The password for the RabbitMQ server"
  value       = module.messaging.password
  sensitive   = true
}

output "rabbitmq_connection_string" {
  description = "The connection string for the RabbitMQ server"
  value       = module.messaging.connection_string
  sensitive   = true
}

output "rabbitmq_exchanges" {
  description = "The list of RabbitMQ exchanges created for the MCA application"
  value       = module.messaging.exchanges
  sensitive   = false
}

output "rabbitmq_queues" {
  description = "The list of RabbitMQ queues created for the MCA application"
  value       = module.messaging.queues
  sensitive   = false
}

# Redis Cache Outputs
output "redis_application_data_endpoint" {
  description = "The connection endpoint for the Redis application data instance"
  value       = module.cache.application_data_endpoint
  sensitive   = false
}

output "redis_user_sessions_endpoint" {
  description = "The connection endpoint for the Redis user sessions instance"
  value       = module.cache.user_sessions_endpoint
  sensitive   = false
}

output "redis_port" {
  description = "The port on which the Redis server accepts connections"
  value       = module.cache.port
  sensitive   = false
}

output "redis_password" {
  description = "The password for the Redis server"
  value       = module.cache.password
  sensitive   = true
}

output "redis_application_data_connection_string" {
  description = "The connection string for the Redis application data instance"
  value       = module.cache.application_data_connection_string
  sensitive   = true
}

output "redis_user_sessions_connection_string" {
  description = "The connection string for the Redis user sessions instance"
  value       = module.cache.user_sessions_connection_string
  sensitive   = true
}

# Redis TTL Settings
output "redis_application_data_ttl" {
  description = "The TTL (Time To Live) for application data in Redis cache"
  value       = "15 minutes"
  sensitive   = false
}

output "redis_user_sessions_ttl" {
  description = "The TTL (Time To Live) for user sessions in Redis cache"
  value       = "24 hours"
  sensitive   = false
}

# S3 Storage Outputs
output "s3_bucket_name" {
  description = "The name of the S3 bucket for document storage in development environment"
  value       = module.storage.bucket_name
  sensitive   = false
}

output "s3_bucket_arn" {
  description = "The ARN of the S3 bucket for document storage"
  value       = module.storage.bucket_arn
  sensitive   = false
}

output "s3_bucket_domain_name" {
  description = "The domain name of the S3 bucket for document storage"
  value       = module.storage.bucket_domain_name
  sensitive   = false
}

output "s3_bucket_region" {
  description = "The region in which the S3 bucket is located"
  value       = module.storage.bucket_region
  sensitive   = false
}

# Development-specific Configuration Outputs
output "environment" {
  description = "The name of the environment (development)"
  value       = "development"
  sensitive   = false
}

output "api_base_url" {
  description = "The base URL for the API gateway in the development environment"
  value       = "http://localhost:8000"
  sensitive   = false
}

output "frontend_url" {
  description = "The URL for the frontend application in the development environment"
  value       = "http://localhost:3000"
  sensitive   = false
}

# Kubernetes Namespace
output "kubernetes_namespace" {
  description = "The Kubernetes namespace for the development environment"
  value       = "mca-development"
  sensitive   = false
}

# Email Service Configuration
output "email_imap_server" {
  description = "The IMAP server for the email service"
  value       = var.email_imap_server
  sensitive   = false
}

output "email_submissions_address" {
  description = "The email address for application submissions"
  value       = "submissions@dollarfunding.com"
  sensitive   = false
}

# Local Development Specific Outputs
output "local_development_guide" {
  description = "URL to the local development guide"
  value       = "https://github.com/dollarfunding/mca-app/wiki/Local-Development-Guide"
  sensitive   = false
}

output "docker_compose_file" {
  description = "Path to the docker-compose file for local development"
  value       = "${path.module}/../../docker-compose.dev.yml"
  sensitive   = false
}

# JWT Authentication Configuration
output "jwt_algorithm" {
  description = "The algorithm used for JWT authentication"
  value       = "RS256"
  sensitive   = false
}

output "jwt_token_expiry" {
  description = "The expiry time for JWT tokens"
  value       = "60 minutes"
  sensitive   = false
}

output "jwt_refresh_token_expiry" {
  description = "The expiry time for JWT refresh tokens"
  value       = "7 days"
  sensitive   = false
}

# Document Processing Configuration
output "document_classification_models_path" {
  description = "Path to the document classification models"
  value       = module.storage.models_path
  sensitive   = false
}

output "ocr_models_path" {
  description = "Path to the OCR models"
  value       = module.storage.ocr_models_path
  sensitive   = false
}