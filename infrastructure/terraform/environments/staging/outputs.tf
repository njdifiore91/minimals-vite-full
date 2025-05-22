# Staging Environment Outputs
# This file exports essential information from the staging environment as Terraform outputs,
# including connection endpoints, credentials, and resource identifiers.

# PostgreSQL Database Outputs
output "postgres_primary_endpoint" {
  description = "The connection endpoint for the primary PostgreSQL database"
  value       = module.database.primary_endpoint
  sensitive   = false
}

output "postgres_read_replica_endpoint" {
  description = "The connection endpoint for the PostgreSQL read replica"
  value       = module.database.read_replica_endpoints[0]
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
  description = "The master username for the PostgreSQL database"
  value       = module.database.username
  sensitive   = true
}

output "postgres_password" {
  description = "The master password for the PostgreSQL database"
  value       = module.database.password
  sensitive   = true
}

output "postgres_connection_string" {
  description = "The connection string for the PostgreSQL database"
  value       = module.database.connection_string
  sensitive   = true
}

output "postgres_read_connection_string" {
  description = "The connection string for the PostgreSQL read replica"
  value       = module.database.read_connection_string
  sensitive   = true
}

# RabbitMQ Messaging Outputs
output "rabbitmq_endpoint" {
  description = "The connection endpoint for the RabbitMQ cluster"
  value       = module.messaging.endpoint
  sensitive   = false
}

output "rabbitmq_management_url" {
  description = "The URL for the RabbitMQ management interface"
  value       = module.messaging.management_url
  sensitive   = false
}

output "rabbitmq_port" {
  description = "The port on which the RabbitMQ cluster accepts connections"
  value       = module.messaging.port
  sensitive   = false
}

output "rabbitmq_vhost" {
  description = "The virtual host for the RabbitMQ cluster"
  value       = module.messaging.vhost
  sensitive   = false
}

output "rabbitmq_username" {
  description = "The username for the RabbitMQ cluster"
  value       = module.messaging.username
  sensitive   = true
}

output "rabbitmq_password" {
  description = "The password for the RabbitMQ cluster"
  value       = module.messaging.password
  sensitive   = true
}

output "rabbitmq_connection_string" {
  description = "The connection string for the RabbitMQ cluster"
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
output "redis_cache_endpoint" {
  description = "The connection endpoint for the Redis cache instance"
  value       = module.cache.cache_endpoint
  sensitive   = false
}

output "redis_session_endpoint" {
  description = "The connection endpoint for the Redis session instance"
  value       = module.cache.session_endpoint
  sensitive   = false
}

output "redis_port" {
  description = "The port on which the Redis cluster accepts connections"
  value       = module.cache.port
  sensitive   = false
}

output "redis_password" {
  description = "The password for the Redis cluster"
  value       = module.cache.password
  sensitive   = true
}

output "redis_cache_connection_string" {
  description = "The connection string for the Redis cache instance"
  value       = module.cache.cache_connection_string
  sensitive   = true
}

output "redis_session_connection_string" {
  description = "The connection string for the Redis session instance"
  value       = module.cache.session_connection_string
  sensitive   = true
}

# S3 Storage Outputs
output "s3_bucket_name" {
  description = "The name of the S3 bucket for document storage in staging environment"
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

# Staging-specific Configuration Outputs
output "environment" {
  description = "The name of the environment (staging)"
  value       = "staging"
  sensitive   = false
}

output "api_base_url" {
  description = "The base URL for the API gateway in the staging environment"
  value       = "https://api-staging.dollarfunding.com"
  sensitive   = false
}

output "frontend_url" {
  description = "The URL for the frontend application in the staging environment"
  value       = "https://staging.dollarfunding.com"
  sensitive   = false
}

# Kubernetes Namespace
output "kubernetes_namespace" {
  description = "The Kubernetes namespace for the staging environment"
  value       = "mca-staging"
  sensitive   = false
}

# Monitoring and Logging Outputs
output "monitoring_dashboard_url" {
  description = "The URL for the monitoring dashboard in the staging environment"
  value       = module.monitoring.dashboard_url
  sensitive   = false
}

output "log_group_name" {
  description = "The name of the log group for the staging environment"
  value       = module.monitoring.log_group_name
  sensitive   = false
}