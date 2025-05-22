# Outputs for the MCA Application Processing System - Production Environment

# Database outputs
output "database_primary_endpoint" {
  description = "The endpoint of the primary PostgreSQL database"
  value       = module.database.primary_endpoint
}

output "database_reader_endpoint" {
  description = "The endpoint for read replicas of the PostgreSQL database"
  value       = module.database.reader_endpoint
}

output "database_port" {
  description = "The port on which the PostgreSQL database accepts connections"
  value       = module.database.port
}

output "database_name" {
  description = "The name of the PostgreSQL database"
  value       = module.database.database_name
}

output "database_connection_string_template" {
  description = "Template for PostgreSQL connection string (password not included)"
  value       = "postgresql://${module.database.username}:PASSWORD@${module.database.primary_endpoint}:${module.database.port}/${module.database.database_name}"
  sensitive   = true
}

# RabbitMQ outputs
output "rabbitmq_endpoint" {
  description = "The endpoint of the RabbitMQ cluster"
  value       = module.messaging.endpoint
}

output "rabbitmq_port" {
  description = "The port on which the RabbitMQ cluster accepts connections"
  value       = module.messaging.port
}

output "rabbitmq_management_url" {
  description = "The URL for the RabbitMQ management interface"
  value       = module.messaging.management_url
}

output "rabbitmq_connection_string_template" {
  description = "Template for RabbitMQ connection string (password not included)"
  value       = "amqp://${module.messaging.username}:PASSWORD@${module.messaging.endpoint}:${module.messaging.port}/"
  sensitive   = true
}

# Redis outputs
output "redis_application_data_endpoint" {
  description = "The endpoint of the Redis cluster for application data"
  value       = module.cache.endpoints["application-data"]
}

output "redis_user_sessions_endpoint" {
  description = "The endpoint of the Redis cluster for user sessions"
  value       = module.cache.endpoints["user-sessions"]
}

output "redis_port" {
  description = "The port on which the Redis cluster accepts connections"
  value       = module.cache.port
}

output "redis_connection_string_template" {
  description = "Template for Redis connection string (auth token not included)"
  value       = "redis://:AUTH_TOKEN@${module.cache.endpoints["application-data"]}:${module.cache.port}/0"
  sensitive   = true
}

# S3 Storage outputs
output "s3_bucket_name" {
  description = "The name of the S3 bucket for document storage"
  value       = module.storage.bucket_names["mca-documents-production"]
}

output "s3_bucket_arn" {
  description = "The ARN of the S3 bucket for document storage"
  value       = module.storage.bucket_arns["mca-documents-production"]
}

output "s3_bucket_domain_name" {
  description = "The domain name of the S3 bucket for document storage"
  value       = module.storage.bucket_domain_names["mca-documents-production"]
}

output "s3_bucket_region" {
  description = "The region of the S3 bucket for document storage"
  value       = module.storage.bucket_regions["mca-documents-production"]
}

# Replica bucket outputs (for disaster recovery)
output "s3_replica_bucket_name" {
  description = "The name of the replica S3 bucket for disaster recovery"
  value       = module.storage.replica_bucket_names["mca-documents-production"]
}

output "s3_replica_bucket_region" {
  description = "The region of the replica S3 bucket for disaster recovery"
  value       = module.storage.replica_bucket_regions["mca-documents-production"]
}

# General outputs
output "environment" {
  description = "The environment name"
  value       = "production"
}

output "region" {
  description = "The primary region where resources are deployed"
  value       = var.aws_region
}

output "replica_region" {
  description = "The replica region for disaster recovery"
  value       = var.replica_region
}