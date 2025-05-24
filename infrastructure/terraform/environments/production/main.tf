# Main Terraform configuration file for the MCA Application Processing System - Production Environment
# This file is the entry point for the production environment infrastructure and calls
# the infrastructure modules with production-specific settings.

# Provider configuration
provider "aws" {
  region = var.aws_region
  # Additional provider settings would be configured here
}

# Remote state configuration is in backend.tf

# Tags common to all resources
locals {
  common_tags = {
    Environment = "production"
    Project     = "MCA Application Processing System"
    ManagedBy   = "Terraform"
  }
}

# PostgreSQL Database Module
# Configures PostgreSQL 14 with primary and two read replicas for production
module "database" {
  source = "../../modules/database"

  # Environment-specific settings
  environment            = "production"
  instance_class         = "db.r6g.2xlarge"  # Larger instance for production
  multi_az               = true              # High availability across AZs
  storage_type           = "gp3"             # General purpose SSD
  allocated_storage      = 200               # GB of storage (larger for production)
  iops                   = 3000              # Higher IOPS for production workloads
  replica_count          = 2                 # Two read replicas for production
  backup_retention_days  = 30                # 30-day backup retention for production
  deletion_protection    = true              # Prevent accidental deletion in production
  
  # Connection pooling settings
  connection_pooling_enabled = true
  connection_pool_min_size   = 20
  connection_pool_max_size   = 100
  
  # Security settings
  encryption_at_rest_enabled = true
  encryption_algorithm       = "AES-256"
  key_rotation_days          = 30            # More frequent key rotation in production
  
  # Performance settings
  performance_insights_enabled = true
  monitoring_interval_seconds  = 5           # More frequent monitoring in production
  
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
  environment        = "production"
  instance_type      = "mq.m5.2xlarge"    # Larger instance for production
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
  environment      = "production"
  node_type        = "cache.r6g.2xlarge"  # Larger instance for production
  shard_count      = 3                   # 3 shards for production
  replicas_per_shard = 2                 # 2 replicas per shard for higher HA
  multi_az         = true                # Deploy across AZs
  
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
  rdb_snapshot_frequency_minutes = 30    # Snapshot every 30 minutes (more frequent than staging)
  aof_enabled = true                     # Append-only file for durability
  
  # High availability settings
  auto_failover_enabled = true
  failover_timeout_seconds = 10          # 10-second failover time (faster than staging)
  
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
  environment = "production"
  
  # Bucket configuration
  buckets = [
    {
      name          = "mca-documents-production"
      versioning    = true
      encryption    = "AES256"
      force_destroy = false  # Prevent accidental destruction in production
    }
  ]
  
  # Lifecycle rules
  lifecycle_rules = [
    {
      bucket        = "mca-documents-production"
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
        days = 2555  # 7-year retention for production (regulatory requirement)
      }
    }
  ]
  
  # Replication configuration for disaster recovery
  replication_enabled = true             # Enable replication for production
  replica_region      = var.replica_region
  
  # Security settings
  block_public_access = true
  encryption_enabled  = true
  encryption_type     = "AES256"
  
  # Monitoring settings
  metrics_enabled     = true
  request_metrics_enabled = true
  object_level_logging_enabled = true    # Enable object-level logging for compliance
  
  tags = local.common_tags
}