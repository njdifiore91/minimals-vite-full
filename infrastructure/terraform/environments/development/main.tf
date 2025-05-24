# Main Terraform configuration file for the MCA Application Processing System - Development Environment
# This file is the entry point for the development environment infrastructure and calls
# the infrastructure modules with development-specific settings.

# Provider configuration
provider "aws" {
  region = var.aws_region
  # Additional provider settings would be configured here
}

# Remote state configuration is in backend.tf

# Tags common to all resources
locals {
  common_tags = {
    Environment = "development"
    Project     = "MCA Application Processing System"
    ManagedBy   = "Terraform"
    Service     = "MCA-Application-Processing"
  }
}

# PostgreSQL Database Module
# Configures PostgreSQL 14 with single instance (no read replicas) for development
module "database" {
  source = "../../modules/database"

  # Environment-specific settings
  environment            = "development"
  db_instance_class      = "db.t3.medium"    # Smaller instance for development
  db_allocated_storage   = 20                # GB of storage (smaller for development)
  db_max_allocated_storage = 50              # Maximum storage growth
  db_backup_retention_period = 1             # 1-day backup retention for development
  
  # Single instance configuration (no read replicas)
  # The module's local.read_replica_count will be 0 for development
  
  # Database credentials (should be replaced with secure values in production)
  db_username            = var.db_username
  db_password            = var.db_password
  db_name                = "mca_application_db"
  
  # Network configuration
  vpc_id                 = var.vpc_id
  subnet_ids             = var.subnet_ids
  security_group_ids     = var.security_group_ids
  
  # Simplified settings for development
  multi_az               = false             # No multi-AZ for development
  skip_final_snapshot    = true              # Skip final snapshot for easier cleanup
  deletion_protection    = false             # Allow deletion in development
  
  # Connection pooling settings for pg with pooling configuration
  # PgBouncer with min 10, max 50 connections as specified in tech spec
  parameter_group_settings = [
    {
      name  = "max_connections"
      value = "100"                         # Lower for development
    },
    {
      name  = "shared_buffers"
      value = "{DBInstanceClassMemory/32768}MB"
    },
    {
      name  = "work_mem"
      value = "16MB"
    },
    {
      name  = "log_min_duration_statement"
      value = "1000"
    }
  ]
  
  tags = local.common_tags
}

# RabbitMQ Messaging Module
# Sets up RabbitMQ with single-node configuration for development
# Using amqplib 0.10.3 for client connections as specified in tech spec
module "messaging" {
  source = "../../modules/messaging"

  # Environment-specific settings
  environment        = "development"
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  
  # Single node configuration for development
  cluster_size       = 1                     # Single node for development
  instance_type      = "mq.t3.micro"         # Smallest instance for development
  engine_version     = "3.10.20"            # Latest compatible version
  
  # Admin credentials (should be replaced with secure values in production)
  admin_username     = var.rabbitmq_username
  admin_password     = var.rabbitmq_password
  
  # Simplified settings for development
  enable_tls         = true                  # Keep TLS enabled for security
  enable_monitoring  = true                  # Enable basic monitoring
  enable_dashboard   = true                  # Enable dashboard for development
  enable_mirrored_queues = false            # No mirrored queues needed for development
  
  # Apply changes immediately in development
  apply_immediately  = true
  
  # Create default exchanges and queues for the MCA document processing pipeline
  create_default_resources = true
  
  # Maintenance window for development (less critical timing)
  maintenance_window_start_time = {
    day_of_week = "SUNDAY"
    time_of_day = "02:00"
    time_zone   = "UTC"
  }
  
  # Logs retention for development
  logs_retention = 3                         # 3 days log retention for development
  
  # AWS account ID for permissions
  aws_account_id     = var.aws_account_id
  
  tags = local.common_tags
}

# Redis Cache Module
# Configures Redis 7.0 with minimal shards for development
# Using ioredis 5.3.2 for client connections as specified in tech spec
module "cache" {
  source = "../../modules/cache"

  # Basic configuration
  name_prefix        = "mca"
  environment        = "development"
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  
  # Environment-specific configuration with minimal resources
  environment_config = {
    development = {
      node_type     = "cache.t3.micro"      # Smallest instance for development
      memory_size   = 0.5                   # GB of memory
      shard_count   = 1                     # Single shard for development
      replica_count = 0                     # No replicas for development
    }
  }
  
  # TTL settings as per requirements
  data_ttl_seconds    = 900                 # 15 minutes TTL for application data
  session_ttl_seconds = 86400               # 24 hours TTL for user sessions
  
  # Eviction policies as specified in tech spec
  cache_eviction_policy  = "allkeys-lru"    # Least recently used eviction for cache
  session_eviction_policy = "noeviction"    # No eviction for sessions
  
  # Simplified settings for development
  enable_automatic_failover = false         # No failover needed for development
  multi_az_enabled          = false         # No multi-AZ for development
  enable_at_rest_encryption = true          # Keep encryption enabled
  enable_transit_encryption = true          # Keep encryption enabled
  enable_aof_persistence    = false         # Disable AOF persistence for development
  snapshot_interval_minutes = 60            # Hourly snapshots
  
  # Monitoring thresholds
  alarm_cpu_threshold_percent    = 90
  alarm_memory_threshold_percent = 90
  
  tags = local.common_tags
}

# S3-compatible Storage Module
# Creates S3-compatible storage bucket for development
# Using @aws-sdk/client-s3 3.509.0 for client connections as specified in tech spec
module "storage" {
  source = "../../modules/storage"

  # Basic configuration
  environment    = "development"
  project        = "mca"
  bucket_prefix  = "dollarfunding"
  bucket_name    = "documents"
  
  # Simplified settings for development
  force_destroy  = true                     # Allow bucket destruction for easier cleanup
  
  # Enable basic features
  enable_versioning      = true             # Keep versioning enabled
  enable_encryption      = true             # Keep encryption enabled
  encryption_algorithm   = "AES256"         # Use AES-256 encryption as specified in tech spec
  
  # Disable advanced features for development
  enable_replication     = false            # No replication for development
  replica_regions        = []               # No replica regions
  enable_object_lock     = false            # No object lock for development
  enable_intelligent_tiering = false        # No intelligent tiering for development
  
  # Simplified lifecycle rules for development
  enable_lifecycle_rules = true
  standard_transition_days = 30             # Transition to IA after 30 days
  archive_storage_class  = "STANDARD_IA"    # Use Standard-IA for archive
  glacier_transition_days = 0               # No Glacier transition for development
  expiration_days        = 365              # 1-year expiration for development
  minimum_retention_days = 1                # Minimum 1-day retention
  
  # Security settings
  block_public_access    = true             # Block public access
  enable_ssl_requests    = true             # Require SSL
  
  # Simplified logging and monitoring
  enable_access_logging  = false            # No access logging for development
  enable_request_metrics = true             # Enable basic metrics
  
  # CORS configuration for frontend access
  enable_cors            = true
  cors_allowed_origins   = ["*"]            # Allow all origins in development
  cors_allowed_methods   = ["GET", "PUT", "POST", "DELETE", "HEAD"]
  cors_allowed_headers   = ["*"]
  cors_expose_headers    = ["ETag"]
  cors_max_age_seconds   = 3600
  
  tags = local.common_tags
}

# Output the endpoints and connection information
output "database_endpoint" {
  description = "The connection endpoint for the PostgreSQL database"
  value       = module.database.primary_endpoint
}

output "database_name" {
  description = "The name of the PostgreSQL database"
  value       = module.database.db_name
}

output "database_port" {
  description = "The port of the PostgreSQL database"
  value       = module.database.db_port
}

output "rabbitmq_endpoints" {
  description = "The connection endpoints for RabbitMQ"
  value       = module.messaging.endpoints
}

output "redis_cache_endpoint" {
  description = "The connection endpoint for the Redis cache"
  value       = module.cache.redis_cache_endpoint
}

output "redis_session_endpoint" {
  description = "The connection endpoint for the Redis session cache"
  value       = module.cache.redis_session_endpoint
}

output "redis_port" {
  description = "The port for Redis connections"
  value       = module.cache.redis_port
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket for document storage"
  value       = "${var.bucket_prefix}-${var.project}-${var.bucket_name}-${var.environment}"
}

# Variables file should be created separately in variables.tf with these variables:
# - aws_region
# - vpc_id
# - subnet_ids
# - security_group_ids
# - db_username
# - db_password
# - rabbitmq_username
# - rabbitmq_password
# - aws_account_id
# - bucket_prefix
# - project
# - bucket_name