# PostgreSQL Database Outputs
# This file defines outputs from the PostgreSQL configuration, including connection strings,
# hostnames, port numbers, and other essential information needed by application services
# to connect to the database.

# Primary Database Connection Information
output "primary_endpoint" {
  description = "The connection endpoint for the primary PostgreSQL database"
  value       = module.postgresql.primary_endpoint
}

output "primary_port" {
  description = "The port on which the primary PostgreSQL database accepts connections"
  value       = module.postgresql.primary_port
}

output "primary_database_name" {
  description = "The name of the primary PostgreSQL database"
  value       = module.postgresql.database_name
}

output "primary_connection_string" {
  description = "The PostgreSQL connection string for the primary database (without credentials)"
  value       = "postgresql://${module.postgresql.primary_endpoint}:${module.postgresql.primary_port}/${module.postgresql.database_name}"
}

output "primary_connection_string_with_auth" {
  description = "The PostgreSQL connection string for the primary database (with credentials)"
  value       = "postgresql://${module.postgresql.master_username}:${module.postgresql.master_password}@${module.postgresql.primary_endpoint}:${module.postgresql.primary_port}/${module.postgresql.database_name}"
  sensitive   = true
}

# Read Replica Connection Information
output "read_replica_endpoints" {
  description = "A list of read replica endpoints for the PostgreSQL database"
  value       = module.postgresql.read_replica_endpoints
}

output "read_replica_ports" {
  description = "A list of ports on which the read replicas accept connections"
  value       = module.postgresql.read_replica_ports
}

output "read_replica_connection_strings" {
  description = "The PostgreSQL connection strings for read replicas (without credentials)"
  value       = [for i, endpoint in module.postgresql.read_replica_endpoints : "postgresql://${endpoint}:${module.postgresql.read_replica_ports[i]}/${module.postgresql.database_name}"]
}

output "read_replica_connection_strings_with_auth" {
  description = "The PostgreSQL connection strings for read replicas (with credentials)"
  value       = [for i, endpoint in module.postgresql.read_replica_endpoints : "postgresql://${module.postgresql.master_username}:${module.postgresql.master_password}@${endpoint}:${module.postgresql.read_replica_ports[i]}/${module.postgresql.database_name}"]
  sensitive   = true
}

# Connection Pooling Information
output "connection_pooling_endpoint" {
  description = "The endpoint for the PgBouncer connection pooling service"
  value       = module.postgresql.connection_pooling_endpoint
}

output "connection_pooling_port" {
  description = "The port on which the PgBouncer connection pooling service accepts connections"
  value       = module.postgresql.connection_pooling_port
}

output "connection_pooling_connection_string" {
  description = "The connection string for the PgBouncer connection pooling service (without credentials)"
  value       = "postgresql://${module.postgresql.connection_pooling_endpoint}:${module.postgresql.connection_pooling_port}/${module.postgresql.database_name}"
}

output "connection_pooling_connection_string_with_auth" {
  description = "The connection string for the PgBouncer connection pooling service (with credentials)"
  value       = "postgresql://${module.postgresql.master_username}:${module.postgresql.master_password}@${module.postgresql.connection_pooling_endpoint}:${module.postgresql.connection_pooling_port}/${module.postgresql.database_name}"
  sensitive   = true
}

output "connection_pooling_config" {
  description = "Configuration details for the PgBouncer connection pooling service"
  value = {
    min_pool_size     = 10
    max_pool_size     = 50
    connection_timeout = 30
    idle_timeout      = 300
    max_client_conn   = 1000
    pool_mode         = "transaction"
  }
}

# Security Group and Network Information
output "security_group_id" {
  description = "The ID of the security group associated with the PostgreSQL database"
  value       = module.postgresql.security_group_id
}

output "subnet_group_name" {
  description = "The name of the subnet group where the PostgreSQL database is deployed"
  value       = module.postgresql.subnet_group_name
}

output "subnet_ids" {
  description = "The IDs of the subnets where the PostgreSQL database is deployed"
  value       = module.postgresql.subnet_ids
}

output "vpc_id" {
  description = "The ID of the VPC where the PostgreSQL database is deployed"
  value       = module.postgresql.vpc_id
}

output "availability_zones" {
  description = "The availability zones where the PostgreSQL database and read replicas are deployed"
  value       = module.postgresql.availability_zones
}

# Database Resource IDs
output "primary_db_instance_id" {
  description = "The ID of the primary PostgreSQL database instance"
  value       = module.postgresql.primary_db_instance_id
}

output "read_replica_db_instance_ids" {
  description = "The IDs of the PostgreSQL read replica database instances"
  value       = module.postgresql.read_replica_db_instance_ids
}

output "db_parameter_group_id" {
  description = "The ID of the DB parameter group used by the PostgreSQL database"
  value       = module.postgresql.db_parameter_group_id
}

output "db_option_group_id" {
  description = "The ID of the DB option group used by the PostgreSQL database"
  value       = module.postgresql.db_option_group_id
}

output "db_subnet_group_id" {
  description = "The ID of the DB subnet group used by the PostgreSQL database"
  value       = module.postgresql.db_subnet_group_id
}

# Monitoring and Logging Configuration
output "enhanced_monitoring_role_arn" {
  description = "The ARN of the IAM role used for enhanced monitoring of the PostgreSQL database"
  value       = module.postgresql.enhanced_monitoring_role_arn
}

output "enhanced_monitoring_interval" {
  description = "The interval, in seconds, between points when enhanced monitoring metrics are collected"
  value       = 15 # 15-second metrics as specified in the technical requirements
}

output "log_types_enabled" {
  description = "The log types enabled for the PostgreSQL database"
  value       = module.postgresql.log_types_enabled
}

output "performance_insights_enabled" {
  description = "Whether Performance Insights is enabled for the PostgreSQL database"
  value       = module.postgresql.performance_insights_enabled
}

output "performance_insights_retention_period" {
  description = "The retention period for Performance Insights data, in days"
  value       = module.postgresql.performance_insights_retention_period
}

# Backup and Recovery Configuration
output "backup_retention_period" {
  description = "The number of days for which automated backups are retained"
  value       = 30 # 30-day retention as specified in the technical requirements
}

output "backup_window" {
  description = "The daily time range during which automated backups are created"
  value       = module.postgresql.backup_window
}

output "maintenance_window" {
  description = "The weekly time range during which system maintenance can occur"
  value       = module.postgresql.maintenance_window
}

output "point_in_time_recovery_enabled" {
  description = "Whether point-in-time recovery is enabled for the PostgreSQL database"
  value       = true # Point-in-time recovery with 5-minute RPO as specified in the technical requirements
}

# Additional Configuration
output "postgres_version" {
  description = "The version of PostgreSQL used by the database"
  value       = "14" # PostgreSQL 14 as specified in the technical requirements
}

output "storage_type" {
  description = "The storage type used by the PostgreSQL database"
  value       = "gp2" # General purpose SSD as specified in the technical requirements
}

output "storage_encrypted" {
  description = "Whether the PostgreSQL database storage is encrypted"
  value       = true # AES-256 encryption as specified in the technical requirements
}

output "multi_az" {
  description = "Whether the PostgreSQL database is deployed in multiple availability zones"
  value       = true # Multi-AZ deployment as specified in the technical requirements
}