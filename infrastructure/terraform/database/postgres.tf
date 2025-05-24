# PostgreSQL 14 RDS Configuration for MCA Application Processing System
# This file defines PostgreSQL resources in a primary-replica configuration with
# environment-specific settings (2 read replicas for production, 1 for staging)

# AWS KMS key for RDS encryption
resource "aws_kms_key" "rds_encryption_key" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  key_usage               = "ENCRYPT_DECRYPT"
  
  tags = {
    Name        = "${var.environment}-rds-encryption-key"
    Environment = var.environment
    Application = "mca-application-processing"
  }
}

# AWS KMS key alias
resource "aws_kms_key_alias" "rds_encryption_key_alias" {
  name          = "alias/${var.environment}-rds-encryption-key"
  target_key_id = aws_kms_key.rds_encryption_key.key_id
}

# DB Subnet Group for RDS instances
resource "aws_db_subnet_group" "postgres" {
  name        = "${var.environment}-postgres-subnet-group"
  description = "Subnet group for PostgreSQL RDS instances"
  subnet_ids  = var.database_subnet_ids
  
  tags = {
    Name        = "${var.environment}-postgres-subnet-group"
    Environment = var.environment
    Application = "mca-application-processing"
  }
}

# DB Parameter Group for PostgreSQL 14
resource "aws_db_parameter_group" "postgres14" {
  name        = "${var.environment}-postgres14-params"
  family      = "postgres14"
  description = "Parameter group for PostgreSQL 14 instances"
  
  # Enable connection pooling parameters
  parameter {
    name  = "max_connections"
    value = var.environment == "production" ? "500" : "200"
  }
  
  # Enable logging parameters
  parameter {
    name  = "log_connections"
    value = "1"
  }
  
  parameter {
    name  = "log_disconnections"
    value = "1"
  }
  
  parameter {
    name  = "log_statement"
    value = "ddl"
  }
  
  # Enable table partitioning parameters
  parameter {
    name  = "max_locks_per_transaction"
    value = "128"
  }
  
  tags = {
    Name        = "${var.environment}-postgres14-params"
    Environment = var.environment
    Application = "mca-application-processing"
  }
}

# Primary PostgreSQL RDS Instance
resource "aws_db_instance" "postgres_primary" {
  identifier              = "${var.environment}-postgres-primary"
  engine                  = "postgres"
  engine_version          = "14"
  instance_class          = var.db_instance_class
  allocated_storage       = var.allocated_storage
  max_allocated_storage   = var.max_allocated_storage
  storage_type            = "gp2"
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.rds_encryption_key.arn
  db_name                 = var.database_name
  username                = var.database_username
  password                = var.database_password
  port                    = 5432
  multi_az                = true
  publicly_accessible     = false
  db_subnet_group_name    = aws_db_subnet_group.postgres.name
  vpc_security_group_ids  = [var.database_security_group_id]
  parameter_group_name    = aws_db_parameter_group.postgres14.name
  backup_retention_period = 30
  backup_window           = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:07:00"
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.environment}-postgres-final-snapshot"
  deletion_protection     = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  monitoring_interval     = 15
  monitoring_role_arn     = var.monitoring_role_arn
  copy_tags_to_snapshot   = true
  auto_minor_version_upgrade = true
  
  tags = {
    Name        = "${var.environment}-postgres-primary"
    Environment = var.environment
    Application = "mca-application-processing"
    Role        = "primary"
  }
  
  lifecycle {
    prevent_destroy = true
  }
}

# Read Replica instances - count based on environment
resource "aws_db_instance" "postgres_replica" {
  count                   = var.environment == "production" ? 2 : 1
  identifier              = "${var.environment}-postgres-replica-${count.index + 1}"
  instance_class          = var.db_instance_class
  replicate_source_db     = aws_db_instance.postgres_primary.identifier
  availability_zone       = element(var.availability_zones, count.index)
  publicly_accessible     = false
  vpc_security_group_ids  = [var.database_security_group_id]
  parameter_group_name    = aws_db_parameter_group.postgres14.name
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.rds_encryption_key.arn
  skip_final_snapshot     = true
  backup_retention_period = 0
  copy_tags_to_snapshot   = true
  auto_minor_version_upgrade = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  monitoring_interval     = 15
  monitoring_role_arn     = var.monitoring_role_arn
  
  tags = {
    Name        = "${var.environment}-postgres-replica-${count.index + 1}"
    Environment = var.environment
    Application = "mca-application-processing"
    Role        = "replica"
  }
}

# PgBouncer Configuration for Connection Pooling
resource "aws_instance" "pgbouncer" {
  count                  = var.environment == "production" ? 2 : 1
  ami                    = var.pgbouncer_ami_id
  instance_type          = "t3.medium"
  subnet_id              = element(var.application_subnet_ids, count.index)
  vpc_security_group_ids = [var.pgbouncer_security_group_id]
  key_name               = var.key_name
  availability_zone      = element(var.availability_zones, count.index)
  
  user_data = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y pgbouncer
    
    # Configure PgBouncer
    cat > /etc/pgbouncer/pgbouncer.ini <<EOL
    [databases]
    * = host=${aws_db_instance.postgres_primary.endpoint} port=5432 dbname=mca
    
    [pgbouncer]
    listen_addr = 0.0.0.0
    listen_port = 6432
    auth_type = md5
    auth_file = /etc/pgbouncer/userlist.txt
    admin_users = postgres
    stats_users = postgres
    pool_mode = transaction
    server_reset_query = DISCARD ALL
    max_client_conn = 10000
    default_pool_size = 50
    min_pool_size = 10
    reserve_pool_size = 5
    reserve_pool_timeout = 3
    server_lifetime = 3600
    server_idle_timeout = 600
    log_connections = 1
    log_disconnections = 1
    application_name_add_host = 1
    EOL
    
    # Create user list file
    cat > /etc/pgbouncer/userlist.txt <<EOL
    "postgres" "${var.database_password}"
    EOL
    
    # Set proper permissions
    chmod 640 /etc/pgbouncer/pgbouncer.ini
    chmod 640 /etc/pgbouncer/userlist.txt
    chown postgres:postgres /etc/pgbouncer/pgbouncer.ini
    chown postgres:postgres /etc/pgbouncer/userlist.txt
    
    # Enable and start PgBouncer service
    systemctl enable pgbouncer
    systemctl restart pgbouncer
  EOF
  
  tags = {
    Name        = "${var.environment}-pgbouncer-${count.index + 1}"
    Environment = var.environment
    Application = "mca-application-processing"
    Role        = "connection-pooler"
  }
}

# CloudWatch Alarms for PostgreSQL monitoring
resource "aws_cloudwatch_metric_alarm" "postgres_cpu_utilization_high" {
  alarm_name          = "${var.environment}-postgres-cpu-utilization-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_primary.id
  }
}

resource "aws_cloudwatch_metric_alarm" "postgres_freeable_memory_low" {
  alarm_name          = "${var.environment}-postgres-freeable-memory-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = "1073741824" # 1 GB in bytes
  alarm_description   = "This metric monitors RDS freeable memory"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_primary.id
  }
}

resource "aws_cloudwatch_metric_alarm" "postgres_connection_count_high" {
  alarm_name          = "${var.environment}-postgres-connection-count-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = var.environment == "production" ? "400" : "150"
  alarm_description   = "This metric monitors RDS connection count"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_primary.id
  }
}

# Variables file
variable "environment" {
  description = "Environment name (e.g., production, staging)"
  type        = string
}

variable "database_subnet_ids" {
  description = "List of subnet IDs for the database subnet group"
  type        = list(string)
}

variable "application_subnet_ids" {
  description = "List of subnet IDs for the application tier"
  type        = list(string)
}

variable "availability_zones" {
  description = "List of availability zones for read replicas"
  type        = list(string)
}

variable "database_security_group_id" {
  description = "Security group ID for the database instances"
  type        = string
}

variable "pgbouncer_security_group_id" {
  description = "Security group ID for the PgBouncer instances"
  type        = string
}

variable "db_instance_class" {
  description = "Instance class for the RDS instances"
  type        = string
  default     = "db.r6g.2xlarge"
}

variable "allocated_storage" {
  description = "Allocated storage for the RDS instances in GB"
  type        = number
  default     = 100
}

variable "max_allocated_storage" {
  description = "Maximum allocated storage for the RDS instances in GB"
  type        = number
  default     = 1000
}

variable "database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "mca"
}

variable "database_username" {
  description = "Username for the database"
  type        = string
  default     = "postgres"
}

variable "database_password" {
  description = "Password for the database"
  type        = string
  sensitive   = true
}

variable "monitoring_role_arn" {
  description = "ARN of the IAM role for enhanced monitoring"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for CloudWatch alarms"
  type        = string
}

variable "pgbouncer_ami_id" {
  description = "AMI ID for the PgBouncer instances"
  type        = string
}

variable "key_name" {
  description = "Key pair name for the PgBouncer instances"
  type        = string
}

# Outputs
output "primary_endpoint" {
  description = "Endpoint of the primary PostgreSQL instance"
  value       = aws_db_instance.postgres_primary.endpoint
}

output "primary_address" {
  description = "Address of the primary PostgreSQL instance"
  value       = aws_db_instance.postgres_primary.address
}

output "replica_endpoints" {
  description = "Endpoints of the PostgreSQL read replicas"
  value       = aws_db_instance.postgres_replica[*].endpoint
}

output "pgbouncer_endpoints" {
  description = "Endpoints of the PgBouncer instances"
  value       = aws_instance.pgbouncer[*].private_ip
}

output "connection_string" {
  description = "PostgreSQL connection string for the primary instance"
  value       = "postgresql://${var.database_username}:${var.database_password}@${aws_db_instance.postgres_primary.endpoint}/${var.database_name}"
  sensitive   = true
}

output "pgbouncer_connection_string" {
  description = "PgBouncer connection string"
  value       = "postgresql://${var.database_username}:${var.database_password}@${aws_instance.pgbouncer[0].private_ip}:6432/${var.database_name}"
  sensitive   = true
}