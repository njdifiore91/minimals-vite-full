# -----------------------------------------------
# PostgreSQL Database Module Outputs
# -----------------------------------------------
# This file exports essential PostgreSQL database information as module outputs,
# including connection endpoints, port numbers, database names, and resource identifiers.
# These outputs are consumed by other Terraform modules and application configuration.

# Primary Database Connection Information
# -----------------------------------------------

output "primary_endpoint" {
  description = "The connection endpoint for the primary PostgreSQL instance"
  value       = aws_db_instance.postgres_primary.endpoint
}

output "primary_address" {
  description = "The hostname of the primary PostgreSQL instance"
  value       = aws_db_instance.postgres_primary.address
}

output "primary_port" {
  description = "The port on which the primary PostgreSQL instance accepts connections"
  value       = aws_db_instance.postgres_primary.port
}

output "primary_id" {
  description = "The ID of the primary PostgreSQL instance"
  value       = aws_db_instance.postgres_primary.id
}

output "primary_arn" {
  description = "The ARN of the primary PostgreSQL instance"
  value       = aws_db_instance.postgres_primary.arn
}

output "primary_availability_zone" {
  description = "The availability zone of the primary PostgreSQL instance"
  value       = aws_db_instance.postgres_primary.availability_zone
}

# Read Replica Connection Information
# -----------------------------------------------

output "replica_endpoints" {
  description = "The connection endpoints for the PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].endpoint
}

output "replica_addresses" {
  description = "The hostnames of the PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].address
}

output "replica_ports" {
  description = "The ports on which the PostgreSQL read replicas accept connections"
  value       = aws_db_instance.postgres_replica[*].port
}

output "replica_ids" {
  description = "The IDs of the PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].id
}

output "replica_arns" {
  description = "The ARNs of the PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].arn
}

output "replica_availability_zones" {
  description = "The availability zones of the PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].availability_zone
}

# Connection Pooling Information
# -----------------------------------------------

output "pgbouncer_endpoints" {
  description = "The endpoints for the PgBouncer connection pooling instances"
  value       = aws_instance.pgbouncer[*].private_ip
}

output "pgbouncer_port" {
  description = "The port on which PgBouncer accepts connections"
  value       = 6432
}

output "pgbouncer_ids" {
  description = "The IDs of the PgBouncer instances"
  value       = aws_instance.pgbouncer[*].id
}

# Database Configuration Information
# -----------------------------------------------

output "database_name" {
  description = "The name of the PostgreSQL database"
  value       = var.database_name
}

output "database_username" {
  description = "The master username for the PostgreSQL database"
  value       = var.database_username
  sensitive   = true
}

output "parameter_group_id" {
  description = "The ID of the DB parameter group"
  value       = aws_db_parameter_group.postgres14.id
}

output "subnet_group_id" {
  description = "The ID of the DB subnet group"
  value       = aws_db_subnet_group.postgres.id
}

output "kms_key_id" {
  description = "The ARN of the KMS key used for encryption"
  value       = aws_kms_key.rds_encryption_key.arn
}

# Security Information
# -----------------------------------------------

output "security_group_id" {
  description = "The ID of the security group used by the database instances"
  value       = var.database_security_group_id
}

output "pgbouncer_security_group_id" {
  description = "The ID of the security group used by the PgBouncer instances"
  value       = var.pgbouncer_security_group_id
}

# Connection Strings
# -----------------------------------------------

output "jdbc_connection_string" {
  description = "JDBC connection string for the primary PostgreSQL instance"
  value       = "jdbc:postgresql://${aws_db_instance.postgres_primary.endpoint}/${var.database_name}"
}

output "jdbc_replica_connection_string" {
  description = "JDBC connection string for the PostgreSQL read replicas (comma-separated)"
  value       = join(",", [for replica in aws_db_instance.postgres_replica : "jdbc:postgresql://${replica.endpoint}/${var.database_name}"])
}

output "jdbc_pgbouncer_connection_string" {
  description = "JDBC connection string for PgBouncer"
  value       = "jdbc:postgresql://${aws_instance.pgbouncer[0].private_ip}:6432/${var.database_name}"
}

output "spring_datasource_url" {
  description = "Spring Boot datasource URL for the primary PostgreSQL instance"
  value       = "jdbc:postgresql://${aws_db_instance.postgres_primary.endpoint}/${var.database_name}"
}

output "spring_replica_datasource_url" {
  description = "Spring Boot datasource URL for the PostgreSQL read replicas (comma-separated)"
  value       = join(",", [for replica in aws_db_instance.postgres_replica : "jdbc:postgresql://${replica.endpoint}/${var.database_name}"])
}

output "node_connection_string" {
  description = "Node.js connection string for the primary PostgreSQL instance"
  value       = "postgresql://${var.database_username}:${var.database_password}@${aws_db_instance.postgres_primary.endpoint}:5432/${var.database_name}"
  sensitive   = true
}

output "node_replica_connection_string" {
  description = "Node.js connection string for the PostgreSQL read replicas (comma-separated)"
  value       = join(",", [for replica in aws_db_instance.postgres_replica : "postgresql://${var.database_username}:${var.database_password}@${replica.endpoint}:5432/${var.database_name}"])
  sensitive   = true
}

output "node_pgbouncer_connection_string" {
  description = "Node.js connection string for PgBouncer"
  value       = "postgresql://${var.database_username}:${var.database_password}@${aws_instance.pgbouncer[0].private_ip}:6432/${var.database_name}"
  sensitive   = true
}

output "python_connection_string" {
  description = "Python connection string for the primary PostgreSQL instance"
  value       = "postgresql://${var.database_username}:${var.database_password}@${aws_db_instance.postgres_primary.endpoint}:5432/${var.database_name}"
  sensitive   = true
}

output "python_replica_connection_string" {
  description = "Python connection string for the PostgreSQL read replicas (comma-separated)"
  value       = join(",", [for replica in aws_db_instance.postgres_replica : "postgresql://${var.database_username}:${var.database_password}@${replica.endpoint}:5432/${var.database_name}"])
  sensitive   = true
}

output "python_pgbouncer_connection_string" {
  description = "Python connection string for PgBouncer"
  value       = "postgresql://${var.database_username}:${var.database_password}@${aws_instance.pgbouncer[0].private_ip}:6432/${var.database_name}"
  sensitive   = true
}

# Monitoring and Logging Information
# -----------------------------------------------

output "cloudwatch_log_groups" {
  description = "The CloudWatch log groups for the PostgreSQL instances"
  value       = {
    primary  = "${var.environment}/rds/postgresql/${aws_db_instance.postgres_primary.id}"
    replicas = [for replica in aws_db_instance.postgres_replica : "${var.environment}/rds/postgresql/${replica.id}"]
  }
}

output "performance_insights_enabled" {
  description = "Whether Performance Insights is enabled for the PostgreSQL instances"
  value       = aws_db_instance.postgres_primary.performance_insights_enabled
}

output "enhanced_monitoring_enabled" {
  description = "Whether Enhanced Monitoring is enabled for the PostgreSQL instances"
  value       = aws_db_instance.postgres_primary.monitoring_interval > 0
}

output "monitoring_interval" {
  description = "The interval, in seconds, between points when Enhanced Monitoring metrics are collected"
  value       = aws_db_instance.postgres_primary.monitoring_interval
}

output "cloudwatch_alarm_arns" {
  description = "The ARNs of the CloudWatch alarms for the PostgreSQL instances"
  value       = {
    cpu_utilization_high    = aws_cloudwatch_metric_alarm.postgres_cpu_utilization_high.arn
    freeable_memory_low     = aws_cloudwatch_metric_alarm.postgres_freeable_memory_low.arn
    connection_count_high   = aws_cloudwatch_metric_alarm.postgres_connection_count_high.arn
  }
}

# Backup and Recovery Information
# -----------------------------------------------

output "backup_retention_period" {
  description = "The backup retention period in days"
  value       = aws_db_instance.postgres_primary.backup_retention_period
}

output "backup_window" {
  description = "The daily time range during which automated backups are created"
  value       = aws_db_instance.postgres_primary.backup_window
}

output "maintenance_window" {
  description = "The weekly time range during which system maintenance can occur"
  value       = aws_db_instance.postgres_primary.maintenance_window
}

output "latest_restorable_time" {
  description = "The latest time to which a database can be restored with point-in-time restore"
  value       = aws_db_instance.postgres_primary.latest_restorable_time
}

# Environment-specific Information
# -----------------------------------------------

output "environment" {
  description = "The deployment environment (production, staging, development)"
  value       = var.environment
}

output "is_production" {
  description = "Whether the current environment is production"
  value       = var.environment == "production"
}

output "read_replica_count" {
  description = "The number of read replicas deployed"
  value       = length(aws_db_instance.postgres_replica)
}