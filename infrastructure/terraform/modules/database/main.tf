/**
 * # PostgreSQL 14 Database Module - Main Configuration
 *
 * This is the primary Terraform configuration file for the PostgreSQL 14 database module.
 * It defines the main database instance with primary-replica architecture, multi-AZ deployment,
 * and connection pooling as required by the MCA Application Processing System.
 *
 * ## Features
 *
 * - PostgreSQL 14 in primary-replica configuration
 * - Multi-AZ deployment for high availability (99.95% uptime guarantee)
 * - Connection pooling with PgBouncer (min 10, max 50 connections)
 * - General purpose SSD with 1000 IOPS baseline
 * - Environment-specific settings (production vs staging)
 * - Automated backups with 30-day retention
 * - Point-in-time recovery with 5-minute RPO
 * - Enhanced monitoring with 15-second metrics
 *
 * ## Usage
 *
 * ```hcl
 * module "postgres_database" {
 *   source = "./modules/database"
 *
 *   environment = "production"
 *   subnet_ids  = ["subnet-12345678", "subnet-87654321"]
 *   db_password = var.database_password
 *
 *   tags = {
 *     Project     = "MCA Application Processing"
 *     Environment = "Production"
 *     Terraform   = "true"
 *   }
 * }
 * ```
 */

# ------------------------------------------------------------------------------
# LOCAL VARIABLES
# ------------------------------------------------------------------------------

locals {
  # Environment-specific settings
  is_production = var.environment == "production"
  is_staging    = var.environment == "staging"
  is_development = var.environment == "development"
  
  # Database instance settings based on environment
  instance_class = local.is_production ? "db.m5.large" : (local.is_staging ? "db.m5.large" : "db.t3.medium")
  
  # Storage settings
  storage_size = local.is_production ? 200 : (local.is_staging ? 100 : 20)
  max_storage  = local.is_production ? 1000 : (local.is_staging ? 500 : 100)
  
  # High availability settings
  multi_az = local.is_production || local.is_staging
  
  # Replica count (managed in replicas.tf)
  # Production: 2 replicas, Staging: 1 replica, Development: 0 replicas
  
  # Database identifier
  db_identifier = "mca-postgres-${var.environment}"
  
  # Default tags to be applied to all resources
  default_tags = {
    Project     = "MCA Application Processing"
    Environment = var.environment
    Terraform   = "true"
    Service     = "PostgreSQL Database"
    Version     = "14"
  }
}

# ------------------------------------------------------------------------------
# DATA SOURCES
# ------------------------------------------------------------------------------

# Get available availability zones in the current region
data "aws_availability_zones" "available" {
  state = "available"
}

# ------------------------------------------------------------------------------
# POSTGRESQL PARAMETER GROUP
# ------------------------------------------------------------------------------

# Create a parameter group for PostgreSQL 14 with optimized settings
resource "aws_db_parameter_group" "postgres14" {
  name        = "${local.db_identifier}-pg14"
  family      = "postgres14"
  description = "Parameter group for PostgreSQL 14 in ${var.environment} environment"
  
  # Connection settings
  parameter {
    name  = "max_connections"
    value = local.is_production ? "200" : (local.is_staging ? "100" : "50")
  }
  
  # Memory settings
  parameter {
    name  = "shared_buffers"
    value = local.is_production ? "8GB" : (local.is_staging ? "4GB" : "1GB")
    apply_method = "pending-reboot"
  }
  
  parameter {
    name  = "work_mem"
    value = local.is_production ? "64MB" : (local.is_staging ? "32MB" : "16MB")
  }
  
  # Query optimization
  parameter {
    name  = "effective_cache_size"
    value = local.is_production ? "24GB" : (local.is_staging ? "12GB" : "3GB")
    apply_method = "pending-reboot"
  }
  
  # Write-ahead log settings
  parameter {
    name  = "wal_buffers"
    value = local.is_production ? "16MB" : (local.is_staging ? "8MB" : "4MB")
    apply_method = "pending-reboot"
  }
  
  parameter {
    name  = "synchronous_commit"
    value = "on"  # Ensures data durability
  }
  
  # Logging settings
  parameter {
    name  = "log_min_duration_statement"
    value = local.is_production ? "1000" : "500"  # Log slow queries (in ms)
  }
  
  parameter {
    name  = "log_statement"
    value = local.is_production ? "none" : "ddl"  # Log DDL statements in non-production
  }
  
  # Vacuum settings
  parameter {
    name  = "autovacuum"
    value = "1"  # Enable autovacuum
  }
  
  parameter {
    name  = "autovacuum_naptime"
    value = local.is_production ? "60" : "120"  # Run more frequently in production
  }
  
  tags = merge(local.default_tags, var.tags)
}

# ------------------------------------------------------------------------------
# POSTGRESQL SUBNET GROUP
# ------------------------------------------------------------------------------

# Create a subnet group for the PostgreSQL database
resource "aws_db_subnet_group" "postgres" {
  name        = "${local.db_identifier}-subnet-group"
  description = "Subnet group for PostgreSQL in ${var.environment} environment"
  subnet_ids  = var.subnet_ids
  
  tags = merge(local.default_tags, var.tags)
}

# ------------------------------------------------------------------------------
# POSTGRESQL OPTION GROUP (for connection pooling)
# ------------------------------------------------------------------------------

# Create an option group for PostgreSQL with PgBouncer connection pooling
resource "aws_db_option_group" "postgres_options" {
  name                 = "${local.db_identifier}-options"
  engine_name          = "postgres"
  major_engine_version = "14"
  
  option {
    option_name = "PGBOUNCER"
    
    option_settings {
      name  = "PGBOUNCER_MIN_POOL_SIZE"
      value = tostring(var.connection_pooling_min)
    }
    
    option_settings {
      name  = "PGBOUNCER_MAX_POOL_SIZE"
      value = tostring(var.connection_pooling_max)
    }
    
    option_settings {
      name  = "PGBOUNCER_IDLE_TIMEOUT"
      value = tostring(var.connection_timeout)
    }
  }
  
  tags = merge(local.default_tags, var.tags)
}

# ------------------------------------------------------------------------------
# POSTGRESQL PRIMARY INSTANCE
# ------------------------------------------------------------------------------

# Create the primary PostgreSQL database instance
resource "aws_db_instance" "postgres_primary" {
  identifier = local.db_identifier
  
  # Engine settings
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class != "" ? var.instance_class : local.instance_class
  
  # Storage settings
  allocated_storage     = var.allocated_storage > 0 ? var.allocated_storage : local.storage_size
  max_allocated_storage = var.max_allocated_storage > 0 ? var.max_allocated_storage : local.max_storage
  storage_type          = var.storage_type
  iops                  = var.storage_type == "io1" || var.storage_type == "gp3" ? var.iops : null
  storage_encrypted     = var.enable_encryption
  kms_key_id            = var.enable_encryption ? var.kms_key_id : null
  
  # Database settings
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = var.db_port
  
  # Network settings
  multi_az               = var.multi_az != null ? var.multi_az : local.multi_az
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = var.vpc_security_group_ids
  publicly_accessible    = false  # Best practice for security
  
  # Parameter and option groups
  parameter_group_name = aws_db_parameter_group.postgres14.name
  option_group_name    = var.enable_connection_pooling ? aws_db_option_group.postgres_options.name : null
  
  # Backup settings
  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window
  copy_tags_to_snapshot   = true
  delete_automated_backups = false
  skip_final_snapshot     = false
  final_snapshot_identifier = "${local.db_identifier}-final-snapshot"
  
  # Maintenance settings
  maintenance_window         = var.maintenance_window
  auto_minor_version_upgrade = true
  apply_immediately          = var.apply_immediately
  
  # Monitoring settings
  monitoring_interval = var.enable_enhanced_monitoring ? var.monitoring_interval : 0
  monitoring_role_arn = var.enable_enhanced_monitoring && var.create_monitoring_role ? aws_iam_role.monitoring[0].arn : null
  
  # Performance Insights
  performance_insights_enabled          = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? var.performance_insights_retention_period : null
  performance_insights_kms_key_id       = var.enable_performance_insights && var.enable_encryption ? var.kms_key_id : null
  
  # Enhanced monitoring logs
  enabled_cloudwatch_logs_exports = [
    "postgresql",
    "upgrade"
  ]
  
  # Security settings
  iam_database_authentication_enabled = var.enable_iam_database_authentication
  deletion_protection                 = var.deletion_protection
  
  # Tags
  tags = merge(
    local.default_tags,
    var.tags,
    {
      Name = local.db_identifier
      Role = "primary"
    }
  )
  
  # Lifecycle policy to prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }
  
  # Timeouts for database operations
  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
  }
  
  depends_on = [
    aws_db_parameter_group.postgres14,
    aws_db_subnet_group.postgres,
    aws_db_option_group.postgres_options
  ]
}

# ------------------------------------------------------------------------------
# MONITORING ROLE (for enhanced monitoring)
# ------------------------------------------------------------------------------

# Create an IAM role for enhanced monitoring if enabled
resource "aws_iam_role" "monitoring" {
  count = var.enable_enhanced_monitoring && var.create_monitoring_role ? 1 : 0
  
  name               = "rds-monitoring-role-${local.db_identifier}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
  
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  ]
  
  tags = merge(local.default_tags, var.tags)
}

# ------------------------------------------------------------------------------
# DNS RECORD (optional)
# ------------------------------------------------------------------------------

# Create a Route 53 DNS record for the database if DNS integration is enabled
resource "aws_route53_record" "primary_dns" {
  count   = var.create_dns_record ? 1 : 0
  zone_id = var.dns_zone_id
  name    = "${local.db_identifier}.${var.dns_domain}"
  type    = "CNAME"
  ttl     = "300"
  records = [aws_db_instance.postgres_primary.address]
}

# ------------------------------------------------------------------------------
# CLOUDWATCH ALARMS
# ------------------------------------------------------------------------------

# Create CloudWatch alarms for critical database metrics
resource "aws_cloudwatch_metric_alarm" "cpu_utilization_alarm" {
  alarm_name          = "${local.db_identifier}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This alarm monitors PostgreSQL CPU utilization"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_primary.id
  }
  
  tags = merge(local.default_tags, var.tags)
}

resource "aws_cloudwatch_metric_alarm" "free_storage_space_alarm" {
  alarm_name          = "${local.db_identifier}-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = "10000000000"  # 10GB in bytes
  alarm_description   = "This alarm monitors PostgreSQL free storage space"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_primary.id
  }
  
  tags = merge(local.default_tags, var.tags)
}

resource "aws_cloudwatch_metric_alarm" "database_connections_alarm" {
  alarm_name          = "${local.db_identifier}-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = local.is_production ? "180" : (local.is_staging ? "90" : "45")  # 90% of max_connections
  alarm_description   = "This alarm monitors PostgreSQL connection count"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_primary.id
  }
  
  tags = merge(local.default_tags, var.tags)
}

# ------------------------------------------------------------------------------
# AUTO-SCALING CONFIGURATION (if enabled)
# ------------------------------------------------------------------------------

# Create an application auto-scaling target for the database if auto-scaling is enabled
resource "aws_appautoscaling_target" "read_replica_count" {
  count              = var.enable_autoscaling ? 1 : 0
  max_capacity       = var.autoscaling_max_capacity
  min_capacity       = var.autoscaling_min_capacity
  resource_id        = "cluster:${aws_db_instance.postgres_primary.id}"
  scalable_dimension = "rds:cluster:ReadReplicaCount"
  service_namespace  = "rds"
}

# Create an auto-scaling policy based on CPU utilization
resource "aws_appautoscaling_policy" "autoscaling_policy" {
  count              = var.enable_autoscaling ? 1 : 0
  name               = "${local.db_identifier}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.read_replica_count[0].resource_id
  scalable_dimension = aws_appautoscaling_target.read_replica_count[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.read_replica_count[0].service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "RDSReaderAverageCPUUtilization"
    }
    target_value       = var.autoscaling_target_cpu
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}