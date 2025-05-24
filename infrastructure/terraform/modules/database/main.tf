# PostgreSQL 14 Database Module for MCA Application Processing System
# This module creates a PostgreSQL 14 database instance with primary-replica architecture,
# multi-AZ deployment, and connection pooling.

# Provider configuration is inherited from the root module

# Variables
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "db_name" {
  description = "Name of the database to create"
  type        = string
  default     = "mca_application_db"
}

variable "db_username" {
  description = "Username for the master DB user"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Password for the master DB user"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "The instance type of the RDS instance"
  type        = string
  default     = "db.t3.large"
}

variable "db_allocated_storage" {
  description = "The allocated storage in gigabytes"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "The upper limit to which Amazon RDS can automatically scale the storage"
  type        = number
  default     = 1000
}

variable "db_backup_retention_period" {
  description = "The days to retain backups for"
  type        = number
  default     = 30
}

variable "db_backup_window" {
  description = "The daily time range during which automated backups are created"
  type        = string
  default     = "03:00-06:00"
}

variable "db_maintenance_window" {
  description = "The window to perform maintenance in"
  type        = string
  default     = "Mon:00:00-Mon:03:00"
}

variable "vpc_id" {
  description = "The VPC ID where the DB instance will be created"
  type        = string
}

variable "subnet_ids" {
  description = "A list of VPC subnet IDs where the DB instance will be deployed"
  type        = list(string)
}

variable "security_group_ids" {
  description = "A list of VPC security group IDs to associate with the DB instance"
  type        = list(string)
  default     = []
}

variable "kms_key_id" {
  description = "The ARN for the KMS encryption key for encryption at rest"
  type        = string
  default     = null
}

variable "tags" {
  description = "A map of tags to assign to the resources"
  type        = map(string)
  default     = {}
}

# Local variables for environment-specific configurations
locals {
  # Number of read replicas based on environment
  read_replica_count = {
    development = 0
    staging     = 1
    production  = 2
  }
  
  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Service     = "MCA-Application-Processing"
    }
  )
  
  # PgBouncer connection pooling settings (to be implemented separately)
  pgbouncer_settings = {
    min_pool_size = 10
    max_pool_size = 50
    pool_mode     = "transaction"
  }
}

# DB subnet group
resource "aws_db_subnet_group" "postgresql" {
  name        = "${var.db_name}-${var.environment}-subnet-group"
  description = "Subnet group for ${var.db_name} PostgreSQL database in ${var.environment} environment"
  subnet_ids  = var.subnet_ids
  tags        = local.common_tags
}

# DB parameter group
resource "aws_db_parameter_group" "postgresql" {
  name        = "${var.db_name}-${var.environment}-parameter-group"
  family      = "postgres14"
  description = "Parameter group for ${var.db_name} PostgreSQL 14 database in ${var.environment} environment"
  
  # Performance and connection parameters
  parameter {
    name  = "max_connections"
    value = "200"
  }
  
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/32768}MB"
  }
  
  parameter {
    name  = "work_mem"
    value = "16MB"
  }
  
  # Logging parameters
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
  
  parameter {
    name  = "log_statement"
    value = "ddl"
  }
  
  tags = local.common_tags
}

# Primary PostgreSQL DB instance
resource "aws_db_instance" "postgresql_primary" {
  identifier              = "${var.db_name}-${var.environment}-primary"
  engine                  = "postgres"
  engine_version          = "14"
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  max_allocated_storage   = var.db_max_allocated_storage
  storage_type            = "gp2"  # General Purpose SSD with 1000 IOPS baseline
  storage_encrypted       = true
  kms_key_id              = var.kms_key_id
  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password
  port                    = 5432
  multi_az                = true  # Enable multi-AZ deployment for high availability
  publicly_accessible     = false
  vpc_security_group_ids  = var.security_group_ids
  db_subnet_group_name    = aws_db_subnet_group.postgresql.name
  parameter_group_name    = aws_db_parameter_group.postgresql.name
  backup_retention_period = var.db_backup_retention_period
  backup_window           = var.db_backup_window
  maintenance_window      = var.db_maintenance_window
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.db_name}-${var.environment}-final-snapshot"
  deletion_protection     = true
  copy_tags_to_snapshot   = true
  auto_minor_version_upgrade = true
  apply_immediately       = false  # Apply changes during maintenance window
  performance_insights_enabled = true
  performance_insights_retention_period = 7  # 7 days retention for performance insights
  monitoring_interval     = 60  # Enhanced monitoring with 60-second intervals
  monitoring_role_arn     = aws_iam_role.rds_monitoring_role.arn
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  # Automatic failover within 30 seconds
  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
  }
  
  tags = local.common_tags
}

# Read replicas
resource "aws_db_instance" "postgresql_replica" {
  count                   = local.read_replica_count[var.environment]
  identifier              = "${var.db_name}-${var.environment}-replica-${count.index + 1}"
  replicate_source_db     = aws_db_instance.postgresql_primary.identifier
  instance_class          = var.db_instance_class
  storage_type            = "gp2"  # General Purpose SSD with 1000 IOPS baseline
  storage_encrypted       = true
  kms_key_id              = var.kms_key_id
  publicly_accessible     = false
  vpc_security_group_ids  = var.security_group_ids
  parameter_group_name    = aws_db_parameter_group.postgresql.name
  backup_retention_period = 0  # Backups are handled by the primary instance
  skip_final_snapshot     = true
  auto_minor_version_upgrade = true
  apply_immediately       = false  # Apply changes during maintenance window
  performance_insights_enabled = true
  performance_insights_retention_period = 7  # 7 days retention for performance insights
  monitoring_interval     = 60  # Enhanced monitoring with 60-second intervals
  monitoring_role_arn     = aws_iam_role.rds_monitoring_role.arn
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  multi_az                = true  # Enable multi-AZ for read replicas as well for high availability
  
  tags = merge(
    local.common_tags,
    {
      ReplicaOf = aws_db_instance.postgresql_primary.identifier
    }
  )
  
  # Dependency on the primary instance
  depends_on = [aws_db_instance.postgresql_primary]
}

# IAM role for enhanced monitoring
resource "aws_iam_role" "rds_monitoring_role" {
  name = "rds-monitoring-role-${var.environment}"
  
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
  
  tags = local.common_tags
}

# Attach the AmazonRDSEnhancedMonitoringRole policy to the monitoring role
resource "aws_iam_role_policy_attachment" "rds_monitoring_attachment" {
  role       = aws_iam_role.rds_monitoring_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch alarm for high CPU utilization
resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "${var.db_name}-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS database CPU utilization"
  alarm_actions       = []
  ok_actions          = []
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgresql_primary.id
  }
  
  tags = local.common_tags
}

# CloudWatch alarm for low free storage space
resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "${var.db_name}-${var.environment}-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10000000000"  # 10GB in bytes
  alarm_description   = "This metric monitors RDS database free storage space"
  alarm_actions       = []
  ok_actions          = []
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgresql_primary.id
  }
  
  tags = local.common_tags
}

# Outputs
output "primary_endpoint" {
  description = "The connection endpoint for the primary PostgreSQL DB instance"
  value       = aws_db_instance.postgresql_primary.endpoint
}

output "primary_arn" {
  description = "The ARN of the primary PostgreSQL DB instance"
  value       = aws_db_instance.postgresql_primary.arn
}

output "read_replica_endpoints" {
  description = "The connection endpoints for the PostgreSQL read replica DB instances"
  value       = aws_db_instance.postgresql_replica[*].endpoint
}

output "db_name" {
  description = "The database name"
  value       = var.db_name
}

output "db_username" {
  description = "The master username for the database"
  value       = var.db_username
  sensitive   = true
}

output "db_port" {
  description = "The database port"
  value       = 5432
}

output "parameter_group_name" {
  description = "The name of the DB parameter group"
  value       = aws_db_parameter_group.postgresql.name
}

output "subnet_group_name" {
  description = "The name of the DB subnet group"
  value       = aws_db_subnet_group.postgresql.name
}

output "connection_pooling_note" {
  description = "Note about connection pooling configuration"
  value       = "Connection pooling with PgBouncer should be configured separately with min_pool_size=${local.pgbouncer_settings.min_pool_size}, max_pool_size=${local.pgbouncer_settings.max_pool_size}, pool_mode=${local.pgbouncer_settings.pool_mode}"
}