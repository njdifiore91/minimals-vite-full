# Main Terraform configuration file for the MCA Application Processing System - Staging Environment
# This file is the entry point for the staging environment infrastructure and calls
# the infrastructure modules with staging-specific settings.

# Provider configuration
provider "aws" {
  region = var.aws_region
  # Additional provider settings would be configured here
}

# Remote state configuration is in backend.tf

# Tags common to all resources
locals {
  common_tags = {
    Environment = "staging"
    Project     = "MCA Application Processing System"
    ManagedBy   = "Terraform"
  }
}

# PostgreSQL Database Module
# Configures PostgreSQL 14 with primary and one read replica for staging
module "database" {
  source = "../../modules/database"

  # Environment-specific settings
  environment            = "staging"
  instance_class         = "db.r6g.xlarge"   # Smaller instance for staging
  multi_az               = true              # High availability across AZs
  storage_type           = "gp3"             # General purpose SSD
  allocated_storage      = 100               # GB of storage (smaller for staging)
  iops                   = 2000              # Lower IOPS for staging workloads
  replica_count          = 1                 # One read replica for staging
  backup_retention_days  = 14                # 14-day backup retention for staging
  deletion_protection    = true              # Prevent accidental deletion in staging
  
  # Connection pooling settings
  connection_pooling_enabled = true
  connection_pool_min_size   = 10
  connection_pool_max_size   = 50
  
  # Security settings
  encryption_at_rest_enabled = true
  encryption_algorithm       = "AES-256"
  key_rotation_days          = 60            # Less frequent key rotation in staging
  
  # Performance settings
  performance_insights_enabled = true
  monitoring_interval_seconds  = 15          # Less frequent monitoring in staging
  
  # High availability settings
  failover_target_auto       = true
  failover_threshold_seconds = 30
  
  tags = local.common_tags
}

# RabbitMQ Messaging Module
# Sets up RabbitMQ cluster with specified exchanges and queues
module "messaging" {
  source = "../../modules/messaging"

  # Environment-specific settings
  environment        = "staging"
  instance_type      = "mq.m5.xlarge"     # Smaller instance for staging
  cluster_node_count = 3                  # 3-node cluster for high availability
  multi_az           = true               # Deploy across AZs
  
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
  tls_version        = "TLS_1_3"
  
  # Persistence settings
  message_persistence_enabled = true
  storage_type                = "ssd"
  
  # High availability settings
  mirrored_queues_enabled = true
  auto_sync_enabled       = true
  
  tags = local.common_tags
}

# Redis Cache Module
# Configures Redis 7.0 cluster for caching with appropriate TTL settings
module "cache" {
  source = "../../modules/cache"

  # Environment-specific settings
  environment      = "staging"
  node_type        = "cache.r6g.xlarge"   # Smaller instance for staging
  shard_count      = 2                    # 2 shards for staging
  replicas_per_shard = 1                  # 1 replica per shard for staging
  multi_az         = true                 # Deploy across AZs
  
  # Cache instances configuration
  cache_instances = [
    {
      name           = "application-data"
      ttl_seconds    = 900               # 15 minutes TTL for application data
      eviction_policy = "allkeys-lru"    # Least recently used eviction
    },
    {
      name           = "user-sessions"
      ttl_seconds    = 86400             # 24 hours TTL for user sessions
      eviction_policy = "noeviction"     # No eviction for sessions
    }
  ]
  
  # Persistence settings
  rdb_snapshot_enabled = true
  rdb_snapshot_frequency_minutes = 60    # Snapshot every 60 minutes (less frequent than production)
  aof_enabled = true                     # Append-only file for durability
  
  # High availability settings
  auto_failover_enabled = true
  failover_timeout_seconds = 15          # 15-second failover time (slower than production)
  
  # Security settings
  encryption_in_transit = true
  encryption_at_rest    = true
  
  tags = local.common_tags
}

# S3-compatible Storage Module
# Creates S3-compatible storage with AES-256 encryption
module "storage" {
  source = "../../modules/storage"

  # Environment-specific settings
  environment = "staging"
  
  # Bucket configuration
  buckets = [
    {
      name          = "mca-documents-staging"
      versioning    = true
      encryption    = "AES256"
      force_destroy = false  # Prevent accidental destruction in staging
    }
  ]
  
  # Lifecycle rules
  lifecycle_rules = [
    {
      bucket        = "mca-documents-staging"
      enabled       = true
      prefix        = ""
      
      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        },
        {
          days          = 365
          storage_class = "DEEP_ARCHIVE"
        }
      ]
      
      expiration = {
        days = 1825  # 5-year retention for staging (shorter than production)
      }
    }
  ]
  
  # Replication configuration - disabled for staging
  replication_enabled = false
  
  # Security settings
  block_public_access = true
  encryption_enabled  = true
  encryption_type     = "AES256"
  
  # Monitoring settings
  metrics_enabled     = true
  request_metrics_enabled = true
  object_level_logging_enabled = false    # Disable object-level logging for staging
  
  tags = local.common_tags
}