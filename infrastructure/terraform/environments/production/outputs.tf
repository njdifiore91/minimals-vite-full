# =============================================================================
# Production Environment Terraform Outputs
# =============================================================================
# This file defines all outputs from the production environment Terraform configuration.
# These outputs are consumed by application configuration and CI/CD pipelines to
# connect to the infrastructure services.
# =============================================================================

# -----------------------------------------------------------------------------
# PostgreSQL Database Outputs
# -----------------------------------------------------------------------------

output "postgresql_primary_endpoint" {
  description = "The connection endpoint for the PostgreSQL primary instance"
  value       = module.postgresql.primary_endpoint
  sensitive   = false
}

output "postgresql_primary_port" {
  description = "The port on which the PostgreSQL primary instance accepts connections"
  value       = module.postgresql.primary_port
  sensitive   = false
}

output "postgresql_replica_endpoints" {
  description = "The connection endpoints for the PostgreSQL read replicas"
  value       = module.postgresql.replica_endpoints
  sensitive   = false
}

output "postgresql_connection_string" {
  description = "The connection string for the PostgreSQL primary instance"
  value       = "postgresql://${module.postgresql.master_username}:${module.postgresql.master_password}@${module.postgresql.primary_endpoint}:${module.postgresql.primary_port}/${module.postgresql.database_name}"
  sensitive   = true
}

output "postgresql_replica_connection_string" {
  description = "The connection string for the PostgreSQL read replicas"
  value       = [for endpoint in module.postgresql.replica_endpoints : "postgresql://${module.postgresql.master_username}:${module.postgresql.master_password}@${endpoint}:${module.postgresql.primary_port}/${module.postgresql.database_name}"]
  sensitive   = true
}

output "postgresql_master_username" {
  description = "The master username for the PostgreSQL database"
  value       = module.postgresql.master_username
  sensitive   = true
}

output "postgresql_master_password" {
  description = "The master password for the PostgreSQL database"
  value       = module.postgresql.master_password
  sensitive   = true
}

output "postgresql_database_name" {
  description = "The name of the default database created"
  value       = module.postgresql.database_name
  sensitive   = false
}

output "postgresql_parameter_group_name" {
  description = "The name of the PostgreSQL parameter group"
  value       = module.postgresql.parameter_group_name
  sensitive   = false
}

# -----------------------------------------------------------------------------
# RabbitMQ Outputs
# -----------------------------------------------------------------------------

output "rabbitmq_endpoints" {
  description = "The connection endpoints for the RabbitMQ cluster nodes"
  value       = module.rabbitmq.endpoints
  sensitive   = false
}

output "rabbitmq_cluster_endpoint" {
  description = "The load-balanced endpoint for the RabbitMQ cluster"
  value       = module.rabbitmq.cluster_endpoint
  sensitive   = false
}

output "rabbitmq_port" {
  description = "The port on which the RabbitMQ cluster accepts connections"
  value       = module.rabbitmq.port
  sensitive   = false
}

output "rabbitmq_management_endpoint" {
  description = "The endpoint for the RabbitMQ management interface"
  value       = module.rabbitmq.management_endpoint
  sensitive   = false
}

output "rabbitmq_management_port" {
  description = "The port for the RabbitMQ management interface"
  value       = module.rabbitmq.management_port
  sensitive   = false
}

output "rabbitmq_username" {
  description = "The username for the RabbitMQ administrator"
  value       = module.rabbitmq.username
  sensitive   = true
}

output "rabbitmq_password" {
  description = "The password for the RabbitMQ administrator"
  value       = module.rabbitmq.password
  sensitive   = true
}

output "rabbitmq_connection_string" {
  description = "The AMQP connection string for the RabbitMQ cluster"
  value       = "amqp://${module.rabbitmq.username}:${module.rabbitmq.password}@${module.rabbitmq.cluster_endpoint}:${module.rabbitmq.port}/"
  sensitive   = true
}

output "rabbitmq_vhost" {
  description = "The virtual host configured in RabbitMQ"
  value       = module.rabbitmq.vhost
  sensitive   = false
}

# -----------------------------------------------------------------------------
# Redis Cache Outputs
# -----------------------------------------------------------------------------

output "redis_cache_endpoint" {
  description = "The connection endpoint for the Redis cache cluster"
  value       = module.redis_cache.endpoint
  sensitive   = false
}

output "redis_cache_port" {
  description = "The port on which the Redis cache cluster accepts connections"
  value       = module.redis_cache.port
  sensitive   = false
}

output "redis_cache_auth_token" {
  description = "The authentication token for the Redis cache cluster"
  value       = module.redis_cache.auth_token
  sensitive   = true
}

output "redis_cache_connection_string" {
  description = "The connection string for the Redis cache cluster"
  value       = "redis://:${module.redis_cache.auth_token}@${module.redis_cache.endpoint}:${module.redis_cache.port}/0"
  sensitive   = true
}

output "redis_cache_nodes" {
  description = "The list of all Redis cache nodes in the cluster"
  value       = module.redis_cache.nodes
  sensitive   = false
}

# -----------------------------------------------------------------------------
# Redis Session Outputs
# -----------------------------------------------------------------------------

output "redis_session_endpoint" {
  description = "The connection endpoint for the Redis session cluster"
  value       = module.redis_session.endpoint
  sensitive   = false
}

output "redis_session_port" {
  description = "The port on which the Redis session cluster accepts connections"
  value       = module.redis_session.port
  sensitive   = false
}

output "redis_session_auth_token" {
  description = "The authentication token for the Redis session cluster"
  value       = module.redis_session.auth_token
  sensitive   = true
}

output "redis_session_connection_string" {
  description = "The connection string for the Redis session cluster"
  value       = "redis://:${module.redis_session.auth_token}@${module.redis_session.endpoint}:${module.redis_session.port}/0"
  sensitive   = true
}

output "redis_session_nodes" {
  description = "The list of all Redis session nodes in the cluster"
  value       = module.redis_session.nodes
  sensitive   = false
}

# -----------------------------------------------------------------------------
# S3 Storage Outputs
# -----------------------------------------------------------------------------

output "s3_documents_bucket_name" {
  description = "The name of the S3 bucket for document storage"
  value       = module.s3_storage.documents_bucket_name
  sensitive   = false
}

output "s3_documents_bucket_arn" {
  description = "The ARN of the S3 bucket for document storage"
  value       = module.s3_storage.documents_bucket_arn
  sensitive   = false
}

output "s3_documents_bucket_region" {
  description = "The region of the S3 bucket for document storage"
  value       = module.s3_storage.documents_bucket_region
  sensitive   = false
}

output "s3_documents_bucket_domain_name" {
  description = "The domain name of the S3 bucket for document storage"
  value       = module.s3_storage.documents_bucket_domain_name
  sensitive   = false
}

output "s3_access_key" {
  description = "The access key for the S3 service account"
  value       = module.s3_storage.access_key
  sensitive   = true
}

output "s3_secret_key" {
  description = "The secret key for the S3 service account"
  value       = module.s3_storage.secret_key
  sensitive   = true
}

output "s3_endpoint" {
  description = "The endpoint for the S3-compatible storage service"
  value       = module.s3_storage.endpoint
  sensitive   = false
}

# -----------------------------------------------------------------------------
# Kubernetes Outputs
# -----------------------------------------------------------------------------

output "kubernetes_api_endpoint" {
  description = "The endpoint for the Kubernetes API server"
  value       = module.kubernetes.api_endpoint
  sensitive   = false
}

output "kubernetes_ca_certificate" {
  description = "The CA certificate for the Kubernetes cluster"
  value       = module.kubernetes.ca_certificate
  sensitive   = true
}

output "kubernetes_token" {
  description = "The token for the Kubernetes service account"
  value       = module.kubernetes.token
  sensitive   = true
}

output "kubernetes_namespace" {
  description = "The Kubernetes namespace for the application"
  value       = "mca-production"
  sensitive   = false
}

# -----------------------------------------------------------------------------
# API Gateway Outputs
# -----------------------------------------------------------------------------

output "api_gateway_endpoint" {
  description = "The endpoint for the Kong API Gateway"
  value       = module.api_gateway.endpoint
  sensitive   = false
}

output "api_gateway_admin_endpoint" {
  description = "The admin endpoint for the Kong API Gateway"
  value       = module.api_gateway.admin_endpoint
  sensitive   = false
}

output "api_gateway_admin_token" {
  description = "The admin token for the Kong API Gateway"
  value       = module.api_gateway.admin_token
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Monitoring Outputs
# -----------------------------------------------------------------------------

output "monitoring_dashboard_url" {
  description = "The URL for the monitoring dashboard"
  value       = module.monitoring.dashboard_url
  sensitive   = false
}

output "monitoring_api_key" {
  description = "The API key for the monitoring service"
  value       = module.monitoring.api_key
  sensitive   = true
}

output "monitoring_app_key" {
  description = "The application key for the monitoring service"
  value       = module.monitoring.app_key
  sensitive   = true
}

# -----------------------------------------------------------------------------
# General Environment Outputs
# -----------------------------------------------------------------------------

output "environment_name" {
  description = "The name of the environment"
  value       = "production"
  sensitive   = false
}

output "region" {
  description = "The primary region for the environment"
  value       = var.region
  sensitive   = false
}

output "secondary_region" {
  description = "The secondary region for disaster recovery"
  value       = var.secondary_region
  sensitive   = false
}

output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.network.vpc_id
  sensitive   = false
}

output "private_subnet_ids" {
  description = "The IDs of the private subnets"
  value       = module.network.private_subnet_ids
  sensitive   = false
}

output "public_subnet_ids" {
  description = "The IDs of the public subnets"
  value       = module.network.public_subnet_ids
  sensitive   = false
}

output "availability_zones" {
  description = "The availability zones used in the environment"
  value       = module.network.availability_zones
  sensitive   = false
}