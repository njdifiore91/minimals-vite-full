# PostgreSQL Database Module Outputs
# This file defines the outputs from the PostgreSQL database module that are consumed by
# other Terraform modules and application configuration for the MCA Application Processing System.
#
# These outputs provide essential connection information, resource identifiers, and configuration
# details needed by the microservices in the MCA Application Processing System to connect to and
# interact with the PostgreSQL database.

#-------------------------------------------------------
# Connection Endpoints
#-------------------------------------------------------

output "db_instance_endpoint" {
  description = "The connection endpoint for the primary PostgreSQL instance"
  value       = try(aws_db_instance.this.endpoint, null)
}

output "db_instance_address" {
  description = "The hostname of the primary PostgreSQL instance"
  value       = try(aws_db_instance.this.address, null)
}

output "db_instance_port" {
  description = "The port on which the PostgreSQL instance accepts connections"
  value       = try(aws_db_instance.this.port, null)
}

output "replica_endpoints" {
  description = "The connection endpoints for the PostgreSQL read replicas"
  value       = try(aws_db_instance.replica[*].endpoint, [])
}

output "replica_addresses" {
  description = "The hostnames of the PostgreSQL read replicas"
  value       = try(aws_db_instance.replica[*].address, [])
}

#-------------------------------------------------------
# Connection Strings
#-------------------------------------------------------

output "connection_string" {
  description = "The connection string for the primary PostgreSQL database"
  value       = "postgresql://${var.username}:${var.password}@${aws_db_instance.this.endpoint}/${var.db_name}"
  sensitive   = true
}

output "replica_connection_strings" {
  description = "The connection strings for the PostgreSQL read replicas"
  value       = [for replica in aws_db_instance.replica : "postgresql://${var.username}:${var.password}@${replica.endpoint}/${var.db_name}"]
  sensitive   = true
}

output "connection_string_without_credentials" {
  description = "The connection string for the primary PostgreSQL database without credentials"
  value       = "postgresql://${aws_db_instance.this.endpoint}/${var.db_name}"
}

output "replica_connection_strings_without_credentials" {
  description = "The connection strings for the PostgreSQL read replicas without credentials"
  value       = [for replica in aws_db_instance.replica : "postgresql://${replica.endpoint}/${var.db_name}"]
}

#-------------------------------------------------------
# JDBC Connection Strings (for Java/Spring Boot Data Service)
#-------------------------------------------------------

output "jdbc_connection_string" {
  description = "The JDBC connection string for the primary PostgreSQL database (for Data Service)"
  value       = "jdbc:postgresql://${aws_db_instance.this.endpoint}/${var.db_name}"
}

output "jdbc_replica_connection_strings" {
  description = "The JDBC connection strings for the PostgreSQL read replicas (for Data Service)"
  value       = [for replica in aws_db_instance.replica : "jdbc:postgresql://${replica.endpoint}/${var.db_name}"]
}

output "jdbc_connection_string_with_params" {
  description = "The JDBC connection string with additional parameters for the primary PostgreSQL database"
  value       = "jdbc:postgresql://${aws_db_instance.this.endpoint}/${var.db_name}?ssl=true&sslmode=require"
}

output "jdbc_replica_connection_strings_with_params" {
  description = "The JDBC connection strings with additional parameters for the PostgreSQL read replicas"
  value       = [for replica in aws_db_instance.replica : "jdbc:postgresql://${replica.endpoint}/${var.db_name}?ssl=true&sslmode=require"]
}

#-------------------------------------------------------
# Node.js Connection Objects (for Email and Notification Services)
#-------------------------------------------------------

output "node_connection_object" {
  description = "Connection object for Node.js applications connecting to the primary database"
  value = {
    host     = aws_db_instance.this.address
    port     = aws_db_instance.this.port
    database = var.db_name
    user     = var.username
    password = var.password
    ssl      = true
    max      = var.connection_pooling_max
    min      = var.connection_pooling_min
    idleTimeoutMillis = 30000
  }
  sensitive = true
}

output "node_replica_connection_objects" {
  description = "Connection objects for Node.js applications connecting to read replicas"
  value = [for replica in aws_db_instance.replica : {
    host     = replica.address
    port     = replica.port
    database = var.db_name
    user     = var.username
    password = var.password
    ssl      = true
    max      = var.connection_pooling_max
    min      = var.connection_pooling_min
    idleTimeoutMillis = 30000
  }]
  sensitive = true
}

#-------------------------------------------------------
# Python Connection Strings (for Document and OCR Services)
#-------------------------------------------------------

output "python_connection_string" {
  description = "The connection string for Python applications connecting to the primary database"
  value       = "postgresql+psycopg2://${var.username}:${var.password}@${aws_db_instance.this.endpoint}/${var.db_name}"
  sensitive   = true
}

output "python_replica_connection_strings" {
  description = "The connection strings for Python applications connecting to read replicas"
  value       = [for replica in aws_db_instance.replica : "postgresql+psycopg2://${var.username}:${var.password}@${replica.endpoint}/${var.db_name}"]
  sensitive   = true
}

#-------------------------------------------------------
# Resource Identifiers
#-------------------------------------------------------

output "db_instance_id" {
  description = "The ID of the primary PostgreSQL instance"
  value       = try(aws_db_instance.this.id, null)
}

output "db_instance_arn" {
  description = "The ARN of the primary PostgreSQL instance"
  value       = try(aws_db_instance.this.arn, null)
}

output "replica_instance_ids" {
  description = "The IDs of the PostgreSQL read replicas"
  value       = try(aws_db_instance.replica[*].id, [])
}

output "replica_instance_arns" {
  description = "The ARNs of the PostgreSQL read replicas"
  value       = try(aws_db_instance.replica[*].arn, [])
}

output "parameter_group_id" {
  description = "The ID of the PostgreSQL parameter group"
  value       = aws_db_parameter_group.this.id
}

output "option_group_id" {
  description = "The ID of the PostgreSQL option group"
  value       = aws_db_option_group.this.id
}

output "security_group_id" {
  description = "The ID of the security group for the PostgreSQL instances"
  value       = aws_security_group.this.id
}

output "subnet_group_id" {
  description = "The ID of the subnet group for the PostgreSQL instances"
  value       = aws_db_subnet_group.this.id
}

output "kms_key_arn" {
  description = "The ARN of the KMS key used for encryption"
  value       = var.kms_key_id
}

#-------------------------------------------------------
# Configuration Details
#-------------------------------------------------------

output "db_name" {
  description = "The name of the PostgreSQL database"
  value       = var.db_name
}

output "engine_version" {
  description = "The version of the PostgreSQL engine"
  value       = aws_db_instance.this.engine_version
}

output "username" {
  description = "The master username for the PostgreSQL database"
  value       = var.username
  sensitive   = true
}

#-------------------------------------------------------
# Connection Pooling
#-------------------------------------------------------

output "connection_pooling_enabled" {
  description = "Whether connection pooling is enabled for the PostgreSQL instances"
  value       = var.connection_pooling_enabled
}

output "connection_pooling_min" {
  description = "The minimum number of connections in the pool"
  value       = var.connection_pooling_min
}

output "connection_pooling_max" {
  description = "The maximum number of connections in the pool"
  value       = var.connection_pooling_max
}

output "connection_pooling_settings" {
  description = "Complete connection pooling settings for application configuration"
  value = {
    enabled = var.connection_pooling_enabled
    min     = var.connection_pooling_min
    max     = var.connection_pooling_max
    idle_timeout = 30000
    connection_timeout = 10000
    max_lifetime = 1800000
  }
}

#-------------------------------------------------------
# Monitoring and Logging
#-------------------------------------------------------

output "enhanced_monitoring_arn" {
  description = "The ARN of the enhanced monitoring role for the PostgreSQL instances"
  value       = var.monitoring_role_arn
}

output "performance_insights_enabled" {
  description = "Whether performance insights are enabled for the PostgreSQL instances"
  value       = var.performance_insights_enabled
}

output "performance_insights_retention_period" {
  description = "The retention period for performance insights data"
  value       = var.performance_insights_retention_period
}

output "log_exports" {
  description = "The types of logs being exported to CloudWatch"
  value       = var.enabled_cloudwatch_logs_exports
}

output "monitoring_interval" {
  description = "The interval, in seconds, between points when Enhanced Monitoring metrics are collected"
  value       = var.monitoring_interval
}

output "monitoring_configuration" {
  description = "Complete monitoring configuration for application integration"
  value = {
    performance_insights_enabled = var.performance_insights_enabled
    performance_insights_retention_period = var.performance_insights_retention_period
    enhanced_monitoring_interval = var.monitoring_interval
    enhanced_monitoring_arn = var.monitoring_role_arn
    log_exports = var.enabled_cloudwatch_logs_exports
    cloudwatch_logs_group = var.cloudwatch_logs_group
    alarm_cpu_threshold = var.alarm_cpu_threshold
    alarm_storage_threshold = var.alarm_storage_threshold
    alarm_memory_threshold = var.alarm_memory_threshold
    alarm_connection_threshold = var.alarm_connection_threshold
  }
}

#-------------------------------------------------------
# Backup and Recovery
#-------------------------------------------------------

output "backup_retention_period" {
  description = "The backup retention period in days"
  value       = var.backup_retention_period
}

output "backup_window" {
  description = "The daily time range during which automated backups are created"
  value       = var.backup_window
}

output "maintenance_window" {
  description = "The weekly time range during which system maintenance can occur"
  value       = var.maintenance_window
}

output "point_in_time_recovery_enabled" {
  description = "Whether point-in-time recovery is enabled for the PostgreSQL instances"
  value       = var.point_in_time_recovery
}

output "backup_configuration" {
  description = "Complete backup configuration for application integration"
  value = {
    backup_retention_period = var.backup_retention_period
    backup_window = var.backup_window
    maintenance_window = var.maintenance_window
    point_in_time_recovery = var.point_in_time_recovery
    final_snapshot_identifier = var.final_snapshot_identifier
    skip_final_snapshot = var.skip_final_snapshot
    delete_automated_backups = var.delete_automated_backups
    long_term_retention_period = var.long_term_retention_period
    enable_cross_region_backup = var.enable_cross_region_backup
    cross_region = var.cross_region
  }
}

#-------------------------------------------------------
# Storage
#-------------------------------------------------------

output "allocated_storage" {
  description = "The amount of allocated storage for the PostgreSQL instances"
  value       = var.allocated_storage
}

output "max_allocated_storage" {
  description = "The maximum amount of storage that can be allocated to the PostgreSQL instances"
  value       = var.max_allocated_storage
}

output "storage_type" {
  description = "The storage type for the PostgreSQL instances"
  value       = var.storage_type
}

output "storage_encrypted" {
  description = "Whether the storage for the PostgreSQL instances is encrypted"
  value       = var.storage_encrypted
}

output "storage_configuration" {
  description = "Complete storage configuration for application integration"
  value = {
    allocated_storage = var.allocated_storage
    max_allocated_storage = var.max_allocated_storage
    storage_type = var.storage_type
    storage_encrypted = var.storage_encrypted
    iops = var.iops
    throughput = var.throughput
  }
}

#-------------------------------------------------------
# High Availability
#-------------------------------------------------------

output "multi_az" {
  description = "Whether the PostgreSQL instances are deployed in multiple availability zones"
  value       = var.multi_az
}

output "availability_zone" {
  description = "The availability zone of the primary PostgreSQL instance"
  value       = try(aws_db_instance.this.availability_zone, null)
}

output "replica_availability_zones" {
  description = "The availability zones of the PostgreSQL read replicas"
  value       = try(aws_db_instance.replica[*].availability_zone, [])
}

output "high_availability_configuration" {
  description = "Complete high availability configuration for application integration"
  value = {
    multi_az = var.multi_az
    availability_zone = aws_db_instance.this.availability_zone
    replica_count = var.replica_count
    replica_availability_zones = aws_db_instance.replica[*].availability_zone
  }
}

#-------------------------------------------------------
# Service-Specific Connection Information
#-------------------------------------------------------

# Data Service (Java/Spring Boot)
output "data_service_connection" {
  description = "Connection information for the Data Service (Java/Spring Boot)"
  value = {
    primary_url = "jdbc:postgresql://${aws_db_instance.this.endpoint}/${var.db_name}?ssl=true&sslmode=require"
    read_urls = [for replica in aws_db_instance.replica : "jdbc:postgresql://${replica.endpoint}/${var.db_name}?ssl=true&sslmode=require"]
    username = var.username
    password = var.password
    driver_class = "org.postgresql.Driver"
    hikari_settings = {
      minimum_idle = var.connection_pooling_min
      maximum_pool_size = var.connection_pooling_max
      idle_timeout = 30000
      connection_timeout = 10000
      max_lifetime = 1800000
    }
  }
  sensitive = true
}

# Email Service (Node.js)
output "email_service_connection" {
  description = "Connection information for the Email Service (Node.js)"
  value = {
    host = aws_db_instance.this.address
    port = aws_db_instance.this.port
    database = var.db_name
    user = var.username
    password = var.password
    ssl = true
    pool = {
      max = var.connection_pooling_max
      min = var.connection_pooling_min
      idleTimeoutMillis = 30000
    }
  }
  sensitive = true
}

# Document Service (Python)
output "document_service_connection" {
  description = "Connection information for the Document Service (Python)"
  value = {
    primary_url = "postgresql+psycopg2://${var.username}:${var.password}@${aws_db_instance.this.endpoint}/${var.db_name}"
    read_urls = [for replica in aws_db_instance.replica : "postgresql+psycopg2://${var.username}:${var.password}@${replica.endpoint}/${var.db_name}"]
    pool_size = var.connection_pooling_max
    max_overflow = 10
    pool_timeout = 30
    pool_recycle = 1800
  }
  sensitive = true
}

# OCR Service (Python)
output "ocr_service_connection" {
  description = "Connection information for the OCR Service (Python)"
  value = {
    primary_url = "postgresql+psycopg2://${var.username}:${var.password}@${aws_db_instance.this.endpoint}/${var.db_name}"
    read_urls = [for replica in aws_db_instance.replica : "postgresql+psycopg2://${var.username}:${var.password}@${replica.endpoint}/${var.db_name}"]
    pool_size = var.connection_pooling_max
    max_overflow = 10
    pool_timeout = 30
    pool_recycle = 1800
  }
  sensitive = true
}

# Notification Service (Node.js)
output "notification_service_connection" {
  description = "Connection information for the Notification Service (Node.js)"
  value = {
    host = aws_db_instance.this.address
    port = aws_db_instance.this.port
    database = var.db_name
    user = var.username
    password = var.password
    ssl = true
    pool = {
      max = var.connection_pooling_max
      min = var.connection_pooling_min
      idleTimeoutMillis = 30000
    }
  }
  sensitive = true
}

#-------------------------------------------------------
# Tags
#-------------------------------------------------------

output "tags" {
  description = "The tags assigned to the PostgreSQL instances"
  value       = var.tags
}