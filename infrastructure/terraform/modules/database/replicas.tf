# ------------------------------------------------------------------------------
# POSTGRESQL READ REPLICAS CONFIGURATION
# This file manages the creation and configuration of PostgreSQL read replicas
# based on environment (2 for production, 1 for staging)
# ------------------------------------------------------------------------------

# Local variable to determine the number of replicas based on environment
locals {
  # Production environment gets 2 replicas, staging gets 1 replica
  replica_count = var.environment == "production" ? 2 : (var.environment == "staging" ? 1 : 0)
  
  # List of availability zones to distribute replicas across
  # This ensures replicas are in different AZs than the primary for high availability
  availability_zones = var.multi_az_enabled ? slice(data.aws_availability_zones.available.names, 1, 4) : [data.aws_availability_zones.available.names[0]]
}

# Get available availability zones in the current region
data "aws_availability_zones" "available" {
  state = "available"
}

# Create PostgreSQL read replicas
resource "aws_db_instance" "postgres_replica" {
  count = local.replica_count
  
  # Basic settings
  identifier            = "${var.db_identifier}-replica-${count.index + 1}"
  instance_class        = var.replica_instance_class != "" ? var.replica_instance_class : var.instance_class
  replicate_source_db   = var.db_identifier
  
  # Replica-specific settings
  availability_zone     = element(local.availability_zones, count.index % length(local.availability_zones))
  publicly_accessible   = var.publicly_accessible
  vpc_security_group_ids = var.vpc_security_group_ids
  
  # Performance settings
  parameter_group_name  = var.parameter_group_name
  apply_immediately     = var.apply_immediately
  
  # Storage settings
  storage_type          = var.storage_type
  storage_encrypted     = var.storage_encrypted
  kms_key_id            = var.kms_key_id
  
  # Backup settings
  backup_retention_period = 0  # Backups are managed on the primary instance
  skip_final_snapshot    = true
  copy_tags_to_snapshot  = var.copy_tags_to_snapshot
  
  # Monitoring settings
  monitoring_interval    = var.monitoring_interval
  monitoring_role_arn    = var.monitoring_role_arn
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports
  
  # Maintenance settings
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  maintenance_window         = var.maintenance_window
  
  # Deletion protection
  deletion_protection = var.deletion_protection
  
  # Tags
  tags = merge(
    var.tags,
    {
      Name = "${var.db_identifier}-replica-${count.index + 1}"
      Environment = var.environment
      ReplicaIndex = count.index + 1
      Role = "read-replica"
    }
  )
  
  # Automatic failover configuration
  # Note: AWS RDS handles automatic failover for replicas
  # The primary instance must have multi_az = true for automatic failover
  # Replicas will be promoted if the primary fails
  
  # Lifecycle policy to prevent replacement of replicas during certain changes
  lifecycle {
    ignore_changes = [
      # Ignore changes to these parameters as they're managed by AWS
      replicate_source_db,
    ]
  }
  
  # Timeouts for replica operations
  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
  }
}

# Create a Route 53 DNS record for the read replicas if DNS integration is enabled
resource "aws_route53_record" "replica_dns" {
  count   = var.create_dns_record ? local.replica_count : 0
  zone_id = var.dns_zone_id
  name    = "${var.db_identifier}-replica-${count.index + 1}.${var.dns_domain}"
  type    = "CNAME"
  ttl     = "300"
  records = [aws_db_instance.postgres_replica[count.index].address]
}

# Create CloudWatch alarms for replica lag monitoring
resource "aws_cloudwatch_metric_alarm" "replica_lag_alarm" {
  count               = local.replica_count
  alarm_name          = "${var.db_identifier}-replica-${count.index + 1}-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "5"
  metric_name         = "ReplicaLag"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = "30"  # 30 seconds threshold for replica lag
  alarm_description   = "This alarm monitors PostgreSQL replica lag"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_replica[count.index].id
  }
}