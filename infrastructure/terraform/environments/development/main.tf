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
  }
}

# PostgreSQL Database Module
# Configures PostgreSQL 14 with a single instance (no read replicas) for development
module "database" {
  source = "../../modules/database"

  # Environment-specific settings
  environment            = "development"
  instance_class         = "db.t4g.medium"  # Smaller instance for development
  multi_az               = false            # Single AZ for development
  storage_type           = "gp3"            # General purpose SSD
  allocated_storage      = 20               # GB of storage (smaller for development)
  iops                   = 1000             # Standard IOPS for development
  replica_count          = 0                # No read replicas for development
  backup_retention_days  = 7                # 7-day backup retention for development
  deletion_protection    = false            # Allow deletion in development
  
  # Connection pooling settings
  connection_pooling_enabled = true
  connection_pool_min_size   = 5
  connection_pool_max_size   = 20
  
  # Security settings
  encryption_at_rest_enabled = true
  encryption_algorithm       = "AES-256"
  key_rotation_days          = 90
  
  # Performance settings
  performance_insights_enabled = true
  monitoring_interval_seconds  = 60         # Less frequent monitoring for development
  
  # High availability settings
  failover_target_auto       = false        # No auto-failover for development
  failover_threshold_seconds = 0            # No failover for development
  
  tags = local.common_tags
}

# RabbitMQ Messaging Module
# Sets up RabbitMQ with a single node configuration for development
module "messaging" {
  source = "../../modules/messaging"

  # Environment-specific settings
  environment        = "development"
  instance_type      = "mq.t3.micro"     # Smallest instance for development
  cluster_node_count = 1                 # Single node for development
  multi_az           = false             # Single AZ for development
  
  # Queue and exchange configuration
  exchanges = [
    {
      name       = "mca.documents"
      type       = "fanout"
      durable    = true
      auto_delete = false
    }
  ]
  
  queues = [
    {
      name       = "document-processing"
      durable    = true
      auto_delete = false
    },
    {
      name       = "data-extraction"
      durable    = true
      auto_delete = false
    },
    {
      name       = "notification"
      durable    = true
      auto_delete = false
    }
  ]
  
  # Bindings between exchanges and queues
  bindings = [
    {
      exchange    = "mca.documents"
      queue       = "document-processing"
      routing_key = "document.#"
    },
    {
      exchange    = "mca.documents"
      queue       = "data-extraction"
      routing_key = "extraction.#"
    },
    {
      exchange    = "mca.documents"
      queue       = "notification"
      routing_key = "notification.#"
    }
  ]
  
  # Security settings
  encryption_enabled = true
  tls_version        = "TLS_1_2"         # TLS 1.2 for development
  
  # Persistence settings
  message_persistence_enabled = true
  storage_type                = "ssd"
  
  # High availability settings
  mirrored_queues_enabled = false        # No mirroring for development
  auto_sync_enabled       = false        # No auto-sync for development
  
  tags = local.common_tags
}

# Redis Cache Module
# Configures Redis 7.0 with minimal shards for development purposes
module "cache" {
  source = "../../modules/cache"

  # Environment-specific settings
  environment      = "development"
  node_type        = "cache.t4g.micro"   # Smallest instance for development
  shard_count      = 1                   # Single shard for development
  replicas_per_shard = 0                 # No replicas for development
  multi_az         = false               # Single AZ for development
  
  # Cache instances configuration
  cache_instances = [
    {
      name           = "application-data"
      ttl_seconds    = 900               # 15 minutes TTL for application data (same as other environments)
      eviction_policy = "allkeys-lru"    # Least recently used eviction
    },
    {
      name           = "user-sessions"
      ttl_seconds    = 86400             # 24 hours TTL for user sessions (same as other environments)
      eviction_policy = "noeviction"     # No eviction for sessions
    }
  ]
  
  # Persistence settings
  rdb_snapshot_enabled = true
  rdb_snapshot_frequency_minutes = 60    # Snapshot every 60 minutes
  aof_enabled = false                    # No AOF for development to reduce overhead
  
  # High availability settings
  auto_failover_enabled = false          # No auto-failover for development
  failover_timeout_seconds = 0           # No failover for development
  
  # Security settings
  encryption_in_transit = true
  encryption_at_rest    = true
  
  tags = local.common_tags
}

# S3-compatible Storage Module
# Creates S3-compatible storage bucket for development environment
module "storage" {
  source = "../../modules/storage"

  # Environment-specific settings
  environment = "development"
  
  # Bucket configuration
  buckets = [
    {
      name          = "mca-documents-development"
      versioning    = true
      encryption    = "AES256"
      force_destroy = true               # Allow force destroy in development
    }
  ]
  
  # Lifecycle rules
  lifecycle_rules = [
    {
      bucket        = "mca-documents-development"
      enabled       = true
      prefix        = ""
      
      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        }
      ]
      
      expiration = {
        days = 90       # 90-day retention for development
      }
    }
  ]
  
  # Replication configuration for disaster recovery
  replication_enabled = false           # No replication for development
  replica_region      = var.replica_region
  
  # Security settings
  block_public_access = true
  encryption_enabled  = true
  encryption_type     = "AES256"
  
  # Monitoring settings
  metrics_enabled     = true
  request_metrics_enabled = true
  
  tags = local.common_tags
}