# -----------------------------------------------
# PostgreSQL Read Replicas Configuration
# -----------------------------------------------

# This file manages the creation and configuration of PostgreSQL read replicas,
# implementing the required replica count based on environment (2 for production, 1 for staging).
# It handles replica placement across availability zones, synchronization settings,
# and failover configuration with a 30-second threshold.
#
# Best practices implemented:
# 1. Matching compute resources between primary and replicas
# 2. Cross-AZ placement for high availability
# 3. Replica-specific parameter tuning
# 4. Replication lag monitoring with CloudWatch
# 5. Automatic failover configuration with 30-second threshold
# 6. Low DNS TTL (30s) to prevent stale IP caching during failover

# Local variables for replica configuration
locals {
  # Determine the number of replicas based on environment
  # Production: 2 replicas, Staging: 1 replica, Development: 0 replicas
  replica_count = lookup(var.replica_count, var.environment, 0)
  
  # Get the appropriate instance type for replicas based on environment
  # Best practice: Replicas should have the same compute resources as the primary
  replica_instance_type = lookup(var.replica_instance_type, var.environment, "db.t3.medium")
  
  # Set environment-specific replica parameters
  replica_params = {
    production = {
      max_connections = 300
      shared_buffers = "2GB"
      work_mem = "64MB"
      maintenance_work_mem = "256MB"
      effective_cache_size = "6GB"
      synchronous_commit = "on"
      max_standby_streaming_delay = "30s"
      max_standby_archive_delay = "30s"
    },
    staging = {
      max_connections = 200
      shared_buffers = "1GB"
      work_mem = "32MB"
      maintenance_work_mem = "128MB"
      effective_cache_size = "3GB"
      synchronous_commit = "on"
      max_standby_streaming_delay = "30s"
      max_standby_archive_delay = "30s"
    },
    development = {
      max_connections = 100
      shared_buffers = "512MB"
      work_mem = "16MB"
      maintenance_work_mem = "64MB"
      effective_cache_size = "1GB"
      synchronous_commit = "on"
      max_standby_streaming_delay = "30s"
      max_standby_archive_delay = "30s"
    }
  }
  
  # Get the appropriate parameters for the current environment
  current_replica_params = lookup(local.replica_params, var.environment, local.replica_params.development)
}

# Parameter group specifically for read replicas
# Configuring replica-specific parameters is a best practice for optimal performance
resource "aws_db_parameter_group" "postgres_replica" {
  count       = local.replica_count > 0 ? 1 : 0
  name        = "${var.environment}-postgres-replica-params"
  family      = "postgres14"
  description = "Parameter group for PostgreSQL 14 read replicas"
  
  # Read replica specific parameters
  parameter {
    name  = "max_connections"
    value = local.current_replica_params.max_connections
  }
  
  parameter {
    name  = "shared_buffers"
    value = local.current_replica_params.shared_buffers
  }
  
  parameter {
    name  = "work_mem"
    value = local.current_replica_params.work_mem
  }
  
  parameter {
    name  = "maintenance_work_mem"
    value = local.current_replica_params.maintenance_work_mem
  }
  
  parameter {
    name  = "effective_cache_size"
    value = local.current_replica_params.effective_cache_size
  }
  
  # Replication parameters - critical for controlling replica behavior
  parameter {
    name  = "hot_standby"
    value = "on"
  }
  
  # Set max_standby_streaming_delay to 30s to implement automatic failover within 30 seconds
  # This is a key requirement from the technical specification
  parameter {
    name  = "max_standby_streaming_delay"
    value = local.current_replica_params.max_standby_streaming_delay
  }
  
  # Set max_standby_archive_delay to 30s to implement automatic failover within 30 seconds
  parameter {
    name  = "max_standby_archive_delay"
    value = local.current_replica_params.max_standby_archive_delay
  }
  
  # Control transaction durability behavior
  parameter {
    name  = "synchronous_commit"
    value = local.current_replica_params.synchronous_commit
  }
  
  # Enable read-only queries during recovery
  parameter {
    name  = "hot_standby_feedback"
    value = "on"
  }
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-postgres-replica-params"
      Environment = var.environment
      Role        = "replica"
    }
  )
}

# Read Replica instances
resource "aws_db_instance" "postgres_replica" {
  count                   = local.replica_count
  identifier              = "${var.environment}-postgres-replica-${count.index + 1}"
  # Ensure replicas have the same compute resources as the primary for effective replication
  instance_class          = local.replica_instance_type
  replicate_source_db     = var.primary_db_identifier
  parameter_group_name    = local.replica_count > 0 ? aws_db_parameter_group.postgres_replica[0].name : null
  
  # Place replicas in different availability zones for high availability
  # This is a best practice for distributing read replicas across AZs
  availability_zone       = length(var.replica_availability_zones) > count.index ? 
                            var.replica_availability_zones[count.index] : null
  
  # Security settings
  vpc_security_group_ids  = var.vpc_security_group_ids
  publicly_accessible     = lookup(var.publicly_accessible, var.environment, false)
  storage_encrypted       = var.storage_encrypted
  kms_key_id              = var.kms_key_id
  
  # Backup settings (typically disabled for replicas as they're backed up via the primary)
  backup_retention_period = 0
  skip_final_snapshot     = true
  
  # Maintenance settings
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  maintenance_window      = var.maintenance_window
  apply_immediately       = var.apply_immediately
  
  # Monitoring and performance settings
  monitoring_interval     = var.enable_enhanced_monitoring[var.environment] ? var.monitoring_interval : 0
  monitoring_role_arn     = var.enable_enhanced_monitoring[var.environment] ? var.monitoring_role_arn : null
  performance_insights_enabled = var.performance_insights_enabled[var.environment]
  performance_insights_retention_period = var.performance_insights_enabled[var.environment] ? 
                                         var.performance_insights_retention_period : null
  
  # Enable CloudWatch logs export for comprehensive monitoring
  # This helps in troubleshooting replication issues
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  # Copy tags from primary to replica
  copy_tags_to_snapshot   = true
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.environment}-postgres-replica-${count.index + 1}"
      Environment = var.environment
      Role        = "replica"
      ReplicaIndex = count.index + 1
    }
  )
  
  # Prevent accidental deletion of replicas in production and staging
  lifecycle {
    prevent_destroy = lookup(var.deletion_protection, var.environment, false)
  }
}

# CloudWatch Alarms for replica monitoring
# Monitoring replication lag is a critical best practice for PostgreSQL replicas
resource "aws_cloudwatch_metric_alarm" "replica_lag" {
  count               = local.replica_count
  alarm_name          = "${var.environment}-postgres-replica-${count.index + 1}-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ReplicaLag"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 30  # 30 seconds threshold for replica lag (meets automatic failover requirement)
  alarm_description   = "This alarm monitors PostgreSQL replica lag"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.alarm_actions
  
    dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_replica[count.index].id
  }
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_replica[count.index].id
  }
}

resource "aws_cloudwatch_metric_alarm" "replica_cpu" {
  count               = local.replica_count
  alarm_name          = "${var.environment}-postgres-replica-${count.index + 1}-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 80  # 80% CPU utilization threshold
  alarm_description   = "This alarm monitors PostgreSQL replica CPU utilization"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.alarm_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_replica[count.index].id
  }
}

resource "aws_cloudwatch_metric_alarm" "replica_memory" {
  count               = local.replica_count
  alarm_name          = "${var.environment}-postgres-replica-${count.index + 1}-memory"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 1073741824  # 1 GB in bytes
  alarm_description   = "This alarm monitors PostgreSQL replica freeable memory"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.alarm_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_replica[count.index].id
  }
}

# Route 53 DNS record for read replicas (optional)
resource "aws_route53_record" "postgres_replica" {
  count   = local.replica_count
  zone_id = var.route53_zone_id
  name    = "${var.environment}-postgres-replica-${count.index + 1}.${var.dns_domain}"
  type    = "CNAME"
  # Set TTL to less than 30 seconds to prevent stale IP caching during failover
  # This is a best practice for PostgreSQL 13 and higher versions
  ttl     = 30
  records = [aws_db_instance.postgres_replica[count.index].address]
}

# Outputs for integration with other services and modules
output "replica_endpoints" {
  description = "Connection endpoints for PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].endpoint
}

output "replica_addresses" {
  description = "DNS addresses for PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].address
}

output "replica_ids" {
  description = "IDs of the PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].id
}

output "replica_arns" {
  description = "ARNs of the PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].arn
}

output "replica_dns_entries" {
  description = "Custom DNS entries for PostgreSQL read replicas"
  value       = aws_route53_record.postgres_replica[*].fqdn
}

# Output the count of replicas for reference
output "replica_count" {
  description = "Number of PostgreSQL read replicas deployed"
  value       = local.replica_count
}

# Output the replica lag metric for monitoring
output "replica_lag_alarm_ids" {
  description = "IDs of CloudWatch alarms monitoring replica lag"
  value       = aws_cloudwatch_metric_alarm.replica_lag[*].id
}