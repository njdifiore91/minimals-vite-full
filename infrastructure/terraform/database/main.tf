# Main Terraform configuration for PostgreSQL database infrastructure
# This file serves as the entry point for the database infrastructure configuration
# for the Merchant Cash Advance (MCA) Application Processing System

# Terraform version and provider requirements
terraform {
  required_version = ">= 1.0.0"

  # Backend configuration for state management
  # Uses the configured backend from the environment-specific configuration
  # State is stored remotely to enable team collaboration and state consistency
  backend "s3" {}

  # Required providers with version constraints
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}

# Provider configuration for AWS resources
# This configures the AWS provider with appropriate region and default tags
provider "aws" {
  region = var.region

  # Default tags applied to all resources created by this provider
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "mca-application-system"
      ManagedBy   = "terraform"
      Component   = "database"
    }
  }
}

# Local variables for database configuration
# These variables define environment-specific settings and common configurations
locals {
  # Environment-specific settings
  is_production = var.environment == "production"
  is_staging    = var.environment == "staging"
  is_development = var.environment == "development"
  
  # Number of read replicas based on environment
  # Production: 2 read replicas, Staging: 1 read replica, Development: 0 read replicas
  read_replica_count = local.is_production ? 2 : (local.is_staging ? 1 : 0)
  
  # Database instance types based on environment
  db_instance_type = local.is_production ? var.production_instance_type : var.staging_instance_type
  
  # Database storage settings
  # Using gp3 for better performance and cost-effectiveness
  db_storage_type       = "gp3"
  db_allocated_storage  = local.is_production ? 100 : (local.is_staging ? 50 : 20)
  db_max_storage        = local.is_production ? 1000 : (local.is_staging ? 500 : 100)
  db_iops               = local.is_production ? 3000 : (local.is_staging ? 1000 : 3000)
  
  # Backup settings
  # Production: 30 days retention, Staging: 7 days retention, Development: 1 day retention
  backup_retention_period = local.is_production ? 30 : (local.is_staging ? 7 : 1)
  
  # Database name and identifier
  db_name       = "mca_${var.environment}"
  db_identifier = "mca-postgres-${var.environment}"
  
  # Tags for resource identification and management
  common_tags = {
    Environment = var.environment
    Project     = "mca-application-system"
    Service     = "database"
    ManagedBy   = "terraform"
    Component   = "postgresql"
  }
}

# Data sources for environment-specific configurations
# These data sources retrieve information about the AWS environment

# Get available availability zones in the current region
data "aws_availability_zones" "available" {
  state = "available"
}

# Get current AWS region for reference
data "aws_region" "current" {}

# Get current AWS account ID for reference
data "aws_caller_identity" "current" {}

# Import database module for PostgreSQL 14 configuration
# This module creates the primary PostgreSQL database with read replicas
module "postgresql" {
  source = "../modules/database"

  # General settings
  environment         = var.environment
  db_name             = local.db_name
  db_identifier       = local.db_identifier
  db_instance_type    = local.db_instance_type
  db_engine_version   = "14"  # PostgreSQL 14 as specified in the requirements
  db_port             = 5432  # Standard PostgreSQL port
  db_username         = var.db_username
  db_password         = var.db_password
  db_family           = "postgres14"  # Parameter group family for PostgreSQL 14
  
  # Storage settings
  storage_type       = local.db_storage_type
  allocated_storage  = local.db_allocated_storage
  max_storage        = local.db_max_storage
  iops               = local.db_iops  # 1000 IOPS baseline for production as specified
  
  # High availability settings
  multi_az           = true  # Multi-AZ deployment for high availability
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 3)
  
  # Read replica settings
  read_replica_count = local.read_replica_count  # 2 for production, 1 for staging
  replica_az_enabled = true  # Distribute read replicas across AZs
  
  # Backup and maintenance settings
  backup_retention_period = local.backup_retention_period  # 30 days for production
  backup_window           = "03:00-05:00"  # UTC time
  maintenance_window      = "sun:05:00-sun:07:00"  # UTC time
  
  # Security settings
  storage_encrypted = true  # AES-256 encryption for data at rest
  kms_key_id        = var.kms_key_id
  enable_iam_auth   = true  # Enable IAM authentication for database
  
  # Network settings
  vpc_id             = var.vpc_id
  subnet_ids         = var.database_subnet_ids
  security_group_ids = var.database_security_group_ids
  publicly_accessible = false  # Database should not be publicly accessible
  
  # Connection pooling settings with PgBouncer
  enable_connection_pooling = true
  min_connections           = 10  # Minimum connections as specified
  max_connections           = 50  # Maximum connections as specified
  connection_timeout        = 30  # 30-second timeout as specified
  
  # Performance settings
  # Parameter group configuration for optimal PostgreSQL performance
  parameter_group_family = "postgres14"
  parameters = [
    {
      name  = "shared_buffers"
      value = local.is_production ? "8GB" : "4GB"
      apply_method = "pending-reboot"
    },
    {
      name  = "max_connections"
      value = local.is_production ? "500" : "200"
      apply_method = "pending-reboot"
    },
    {
      name  = "work_mem"
      value = local.is_production ? "64MB" : "32MB"
      apply_method = "immediate"
    },
    {
      name  = "maintenance_work_mem"
      value = local.is_production ? "1GB" : "512MB"
      apply_method = "immediate"
    },
    {
      name  = "effective_cache_size"
      value = local.is_production ? "24GB" : "12GB"
      apply_method = "immediate"
    },
    {
      name  = "log_connections"
      value = "on"
      apply_method = "immediate"
    },
    {
      name  = "log_disconnections"
      value = "on"
      apply_method = "immediate"
    },
    {
      name  = "log_statement"
      value = local.is_production ? "ddl" : "all"
      apply_method = "immediate"
    },
    {
      name  = "log_min_duration_statement"
      value = local.is_production ? "1000" : "100"  # Log slow queries (ms)
      apply_method = "immediate"
    }
  ]
  
  # Monitoring settings
  # Enhanced monitoring with 15-second metrics as specified in requirements
  monitoring_interval = 15
  create_monitoring_role = true
  enable_performance_insights = true
  performance_insights_retention_period = 7  # 7 days retention for performance insights
  enable_enhanced_monitoring = true
  monitoring_role_arn = var.monitoring_role_arn
  
  # Tags
  tags = local.common_tags
}

# Import backup module for database backups and point-in-time recovery
# This module configures automated backups, point-in-time recovery, and long-term retention
# Ensures 7-year retention period for database archival as specified in requirements
module "database_backup" {
  source = "../modules/database/backup"

  # General settings
  environment   = var.environment
  db_identifier = local.db_identifier
  region        = var.region
  
  # Backup settings
  backup_retention_period = local.backup_retention_period  # 30 days for production
  enable_point_in_time_recovery = true  # Enable point-in-time recovery
  recovery_point_objective = 5  # 5-minute RPO as specified
  
  # Long-term backup settings for compliance
  # 7-year retention period for database archival as specified
  enable_long_term_retention = true
  long_term_retention_period = 2555  # 7 years in days
  
  # Snapshot settings
  snapshot_identifier_prefix = "mca-${var.environment}"
  create_final_snapshot = true
  final_snapshot_identifier = "mca-${var.environment}-final-${formatdate("YYYY-MM-DD", timestamp())}"
  
  # Cross-region replication for disaster recovery (production only)
  enable_cross_region_backup = local.is_production
  cross_region_destination   = local.is_production ? var.dr_region : ""
  
  # Encryption settings
  encryption_enabled = true  # AES-256 encryption for backups
  kms_key_id         = var.kms_key_id
  
  # Monitoring and alerting
  enable_monitoring = true
  monitoring_sns_topic_arn = var.monitoring_sns_topic_arn
  
  # Tags
  tags = merge(local.common_tags, {
    BackupType = "automated"
    RetentionPeriod = local.is_production ? "7-years" : "30-days"
  })
  
  # Dependencies
  depends_on = [module.postgresql]
}

# Import replicas module for read replica configuration
# This module creates and configures read replicas based on environment
# Production: 2 read replicas, Staging: 1 read replica as specified in requirements
module "database_replicas" {
  source = "../modules/database/replicas"

  # General settings
  environment   = var.environment
  db_identifier = local.db_identifier
  
  # Read replica settings
  read_replica_count = local.read_replica_count  # 2 for production, 1 for staging
  replica_instance_type = local.is_production ? var.production_replica_instance_type : var.staging_replica_instance_type
  
  # Availability zone settings
  availability_zones = slice(data.aws_availability_zones.available.names, 0, local.read_replica_count)
  
  # Performance settings
  enable_performance_insights = true
  performance_insights_retention_period = 7  # 7 days retention for performance insights
  
  # Monitoring settings
  monitoring_interval = 15  # Enhanced monitoring with 15-second metrics
  
  # Failover settings
  enable_auto_failover = true
  failover_target = local.is_production  # Enable failover target for production
  
  # Tags
  tags = merge(local.common_tags, {
    ReplicaType = "read"
  })
  
  # Dependencies
  depends_on = [module.postgresql]
}