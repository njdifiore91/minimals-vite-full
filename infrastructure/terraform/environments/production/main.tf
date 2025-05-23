# Main Terraform configuration file for the MCA Application Processing System - Production Environment
# This file is the entry point for the production environment infrastructure and calls
# the infrastructure modules with production-specific settings.

# Provider configuration
provider "aws" {
  region = var.aws_region
  # Additional provider settings would be configured here
}

# Kubernetes provider configuration for monitoring resources
provider "kubernetes" {
  config_path = var.kubernetes_config_path
  config_context = var.kubernetes_config_context
}

# Helm provider configuration for Prometheus and Grafana
provider "helm" {
  kubernetes {
    config_path = var.kubernetes_config_path
    config_context = var.kubernetes_config_context
  }
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
  instance_class         = "db.r6g.xlarge"  # Production-grade instance
  multi_az               = true             # High availability across AZs
  storage_type           = "gp3"            # General purpose SSD
  allocated_storage      = 100              # GB of storage
  iops                   = 3000             # Higher IOPS for production
  replica_count          = 2                # Two read replicas for production
  backup_retention_days  = 30               # 30-day backup retention
  deletion_protection    = true             # Prevent accidental deletion
  
  # Connection pooling settings
  connection_pooling_enabled = true
  connection_pool_min_size   = 10
  connection_pool_max_size   = 50
  
  # Security settings
  encryption_at_rest_enabled = true
  encryption_algorithm       = "AES-256"
  key_rotation_days          = 90
  
  # Performance settings
  performance_insights_enabled = true
  monitoring_interval_seconds  = 15
  
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
  instance_type      = "mq.m5.large"  # Production-grade instance
  cluster_node_count = 3              # 3-node cluster for high availability
  multi_az           = true           # Deploy across AZs
  
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
  node_type        = "cache.r6g.large"  # Production-grade instance
  shard_count      = 3                  # 3 shards for horizontal scaling
  replicas_per_shard = 1                # 1 replica per shard for HA
  multi_az         = true               # Deploy across AZs
  
  # Cache instances configuration
  cache_instances = [
    {
      name           = "application-data"
      ttl_seconds    = 900              # 15 minutes TTL for application data
      eviction_policy = "allkeys-lru"   # Least recently used eviction
    },
    {
      name           = "user-sessions"
      ttl_seconds    = 86400            # 24 hours TTL for user sessions
      eviction_policy = "noeviction"    # No eviction for sessions
    }
  ]
  
  # Persistence settings
  rdb_snapshot_enabled = true
  rdb_snapshot_frequency_minutes = 60   # Snapshot every 60 minutes
  aof_enabled = true                    # Append-only file for durability
  
  # High availability settings
  auto_failover_enabled = true
  failover_timeout_seconds = 15         # 15-second failover time
  
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
      force_destroy = false
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
        }
      ]
      
      expiration = {
        days = 2555  # 7 years retention
      }
    }
  ]
  
  # Replication configuration for disaster recovery
  replication_enabled = true
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

# Monitoring Module
# Deploys Prometheus and Grafana for monitoring the MCA Application Processing System
module "monitoring" {
  source = "../../modules/monitoring"

  # Environment-specific settings
  environment = "production"
  cluster_name = var.cluster_name
  namespace = "monitoring"
  app_namespace = "mca"
  
  # Prometheus configuration
  prometheus_storage_enabled = true
  prometheus_storage_class = "gp2"
  prometheus_storage_size = "50Gi"
  prometheus_retention_period = "30d"
  
  # Grafana configuration
  grafana_admin_password = var.grafana_admin_password
  grafana_storage_enabled = true
  grafana_storage_class = "gp2"
  grafana_storage_size = "10Gi"
  grafana_ingress_enabled = true
  grafana_ingress_hosts = ["grafana.${var.domain_name}"]
  grafana_ingress_annotations = {
    "kubernetes.io/ingress.class" = "nginx"
    "cert-manager.io/cluster-issuer" = "letsencrypt-prod"
  }
  grafana_ingress_tls = [
    {
      hosts = ["grafana.${var.domain_name}"]
      secretName = "grafana-tls"
    }
  ]
  grafana_root_url = "https://grafana.${var.domain_name}"
  
  # PostgreSQL exporter configuration
  postgres_exporter_enabled = true
  postgres_host = module.database.primary_endpoint
  postgres_port = 5432
  postgres_user = var.db_username
  postgres_password = var.db_password
  postgres_database = var.db_name
  
  # RabbitMQ exporter configuration
  rabbitmq_exporter_enabled = true
  rabbitmq_host = module.messaging.rabbitmq_endpoint
  rabbitmq_port = 15672
  rabbitmq_user = var.rabbitmq_username
  rabbitmq_password = var.rabbitmq_password
  
  # Redis exporter configuration
  redis_exporter_enabled = true
  redis_host = module.cache.redis_endpoint
  redis_port = 6379
  redis_password = var.redis_auth_token
  
  # CloudWatch exporter for S3 metrics
  cloudwatch_exporter_enabled = true
  cloudwatch_exporter_role = "arn:aws:iam::${var.aws_account_id}:role/prometheus-cloudwatch-exporter"
  aws_region = var.aws_region
  
  # Service monitors
  email_service_monitor_enabled = true
  document_service_monitor_enabled = true
  ocr_service_monitor_enabled = true
  data_service_monitor_enabled = true
  notification_service_monitor_enabled = true
  api_gateway_service_monitor_enabled = true
  
  # Alert thresholds
  sla_processing_time_threshold = 300  # 5 minutes
  ocr_accuracy_threshold = 99  # 99%
  queue_depth_threshold = 1000
  api_response_time_threshold = 1  # 1 second
  
  # Tags
  tags = local.common_tags
}