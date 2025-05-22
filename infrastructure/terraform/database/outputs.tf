# PostgreSQL Database Outputs
# This file defines outputs from the PostgreSQL configuration, including connection strings,
# hostnames, port numbers, and other essential information needed by application services
# to connect to the database.

# Primary Database Connection Information
output "primary_db_endpoint" {
  description = "The connection endpoint for the primary PostgreSQL database"
  value       = module.postgres.primary_db_endpoint
}

output "primary_db_address" {
  description = "The hostname of the primary PostgreSQL database"
  value       = module.postgres.primary_db_address
}

output "primary_db_port" {
  description = "The port on which the primary PostgreSQL database accepts connections"
  value       = module.postgres.primary_db_port
}

output "primary_db_name" {
  description = "The name of the primary PostgreSQL database"
  value       = module.postgres.primary_db_name
}

output "primary_db_username" {
  description = "The master username for the primary PostgreSQL database"
  value       = module.postgres.primary_db_username
  sensitive   = true
}

output "primary_db_connection_string" {
  description = "The PostgreSQL connection string for the primary database (without password)"
  value       = "postgresql://${module.postgres.primary_db_username}@${module.postgres.primary_db_endpoint}/${module.postgres.primary_db_name}"
  sensitive   = true
}

# Read Replica Connection Details
output "read_replica_endpoints" {
  description = "A list of connection endpoints for the PostgreSQL read replicas"
  value       = module.postgres.read_replica_endpoints
}

output "read_replica_addresses" {
  description = "A list of hostnames for the PostgreSQL read replicas"
  value       = module.postgres.read_replica_addresses
}

output "read_replica_connection_strings" {
  description = "A list of PostgreSQL connection strings for read replicas (without passwords)"
  value       = [for endpoint in module.postgres.read_replica_endpoints : "postgresql://${module.postgres.primary_db_username}@${endpoint}/${module.postgres.primary_db_name}"]
  sensitive   = true
}

# Connection Pooling Endpoints
output "connection_pooling_endpoint" {
  description = "The endpoint for the PostgreSQL connection pooling service"
  value       = module.postgres.connection_pooling_endpoint
}

output "connection_pooling_address" {
  description = "The hostname for the PostgreSQL connection pooling service"
  value       = module.postgres.connection_pooling_address
}

output "connection_pooling_port" {
  description = "The port on which the PostgreSQL connection pooling service accepts connections"
  value       = module.postgres.connection_pooling_port
}

output "connection_pooling_connection_string" {
  description = "The PostgreSQL connection string for the connection pooling service (without password)"
  value       = "postgresql://${module.postgres.primary_db_username}@${module.postgres.connection_pooling_endpoint}/${module.postgres.primary_db_name}"
  sensitive   = true
}

# Security Group IDs and Network Information
output "db_security_group_id" {
  description = "The ID of the security group associated with the PostgreSQL database"
  value       = module.postgres.db_security_group_id
}

output "db_subnet_group_name" {
  description = "The name of the DB subnet group used by the PostgreSQL database"
  value       = module.postgres.db_subnet_group_name
}

output "db_parameter_group_name" {
  description = "The name of the DB parameter group used by the PostgreSQL database"
  value       = module.postgres.db_parameter_group_name
}

output "db_option_group_name" {
  description = "The name of the DB option group used by the PostgreSQL database"
  value       = module.postgres.db_option_group_name
}

# Database Resource IDs
output "primary_db_resource_id" {
  description = "The resource ID of the primary PostgreSQL database"
  value       = module.postgres.primary_db_resource_id
}

output "read_replica_resource_ids" {
  description = "A list of resource IDs for the PostgreSQL read replicas"
  value       = module.postgres.read_replica_resource_ids
}

output "db_cluster_resource_id" {
  description = "The resource ID of the PostgreSQL DB cluster"
  value       = module.postgres.db_cluster_resource_id
}

# Monitoring and Logging Configuration
output "enhanced_monitoring_arn" {
  description = "The ARN of the enhanced monitoring role for the PostgreSQL database"
  value       = module.postgres.enhanced_monitoring_arn
}

output "cloudwatch_log_group_name" {
  description = "The name of the CloudWatch log group for PostgreSQL database logs"
  value       = module.postgres.cloudwatch_log_group_name
}

output "performance_insights_enabled" {
  description = "Whether Performance Insights is enabled for the PostgreSQL database"
  value       = module.postgres.performance_insights_enabled
}

output "performance_insights_kms_key_id" {
  description = "The KMS key ID used for encrypting Performance Insights data"
  value       = module.postgres.performance_insights_kms_key_id
  sensitive   = true
}

# Environment-specific Outputs
output "environment" {
  description = "The environment for which the PostgreSQL database is configured (production, staging, development)"
  value       = var.environment
}

output "replica_count" {
  description = "The number of read replicas configured for the PostgreSQL database"
  value       = var.environment == "production" ? 2 : (var.environment == "staging" ? 1 : 0)
}

# Encryption Information
output "storage_encrypted" {
  description = "Whether the PostgreSQL database storage is encrypted"
  value       = module.postgres.storage_encrypted
}

output "kms_key_id" {
  description = "The KMS key ID used for encrypting the PostgreSQL database storage"
  value       = module.postgres.kms_key_id
  sensitive   = true
}

# Backup Configuration
output "backup_retention_period" {
  description = "The backup retention period for the PostgreSQL database in days"
  value       = module.postgres.backup_retention_period
}

output "backup_window" {
  description = "The daily time range during which automated backups are created for the PostgreSQL database"
  value       = module.postgres.backup_window
}

output "maintenance_window" {
  description = "The weekly time range during which system maintenance can occur for the PostgreSQL database"
  value       = module.postgres.maintenance_window
}