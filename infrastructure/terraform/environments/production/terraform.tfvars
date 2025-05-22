# =============================================================================
# MCA Application Processing System - Production Environment Configuration
# =============================================================================
# This file contains the actual values for variables defined in variables.tf,
# specific to the production environment. It configures large instance sizes,
# full high availability features, and production-specific settings for all
# infrastructure components.
# =============================================================================

# Global Settings
# -----------------------------------------------------------------------------
environment = "production"
region      = "us-east-1"  # Primary region for production

# Tags applied to all resources
tags = {
  Environment     = "production"
  Project         = "MCA Application Processing"
  DataClassification = "confidential"
  BusinessUnit    = "Funding Operations"
  CostCenter      = "FO-2023-001"
  ManagedBy       = "Terraform"
}

# Database Configuration (PostgreSQL)
# -----------------------------------------------------------------------------
# Large instance sizes for production with 2 read replicas
db_instance_class         = "db.r5.2xlarge"  # Large instance for primary
db_replica_instance_class = "db.r5.xlarge"   # Slightly smaller for replicas

# Storage configuration with high capacity and growth potential
db_allocated_storage      = 500  # 500GB initial storage
db_max_allocated_storage  = 2000 # Can grow up to 2TB

# High availability and backup settings
multi_az                  = true
backup_retention_period   = 30   # 30 days retention for compliance
backup_window             = "03:00-06:00"  # UTC time window for backups
maintenance_window        = "Sun:06:00-Sun:10:00"  # Weekly maintenance window

# Security settings
storage_encrypted         = true  # Encryption at rest
deletion_protection       = true  # Prevent accidental deletion
skip_final_snapshot       = false # Always create final snapshot

# Performance and monitoring
monitoring_interval                   = 15  # Enhanced monitoring every 15 seconds
performance_insights_enabled          = true
performance_insights_retention_period = 731 # Paid tier (2 years)

# Connection settings
max_connections           = 1000  # High connection limit for production
connection_timeout        = 60    # Longer timeout for complex operations

# Messaging Configuration (RabbitMQ)
# -----------------------------------------------------------------------------
# VPC and subnet configuration for RabbitMQ
# Note: These values are placeholders and should be replaced with actual VPC and subnet IDs
vpc_id           = "vpc-0123456789abcdef0"
subnet_ids       = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1", "subnet-0123456789abcdef2"]
security_group_id = "sg-0123456789abcdef0"

# Security settings
kms_key_id       = "arn:aws:kms:us-east-1:123456789012:key/abcd1234-a123-456a-a12b-a123b4cd56ef"
ca_cert_file     = "/infrastructure/terraform/messaging/certs/ca.pem"

# Monitoring
sns_topic_arn    = "arn:aws:sns:us-east-1:123456789012:rabbitmq-alarms"

# Cache Configuration (Redis)
# -----------------------------------------------------------------------------
# Network configuration for Redis
# Note: These values are placeholders and should be replaced with actual VPC and subnet IDs
vpc_id                = "vpc-0123456789abcdef0"
redis_subnet_ids      = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1", "subnet-0123456789abcdef2"]
app_security_group_ids = ["sg-0123456789abcdef0"]

# Instance configuration - large instances for production
redis_node_type       = "cache.r6g.2xlarge"  # Large memory-optimized instances
enable_data_tiering   = true  # Enable data tiering for cost optimization

# Cluster configuration - full redundancy for production
app_data_num_shards         = 3  # 3 shards for horizontal scaling
app_data_replicas_per_shard = 1  # 1 replica per shard for high availability
user_sessions_num_shards         = 3
user_sessions_replicas_per_shard = 1

# TTL settings as per requirements
app_data_ttl_seconds      = 900    # 15 minutes for application data
user_sessions_ttl_seconds = 86400  # 24 hours for user sessions

# Eviction policies
app_data_eviction_policy      = "allkeys-lru"  # Least recently used for cache
user_sessions_eviction_policy = "noeviction"   # No eviction for sessions

# Persistence and backup
enable_aof_persistence    = true
aof_persistence_interval  = "everysec"
snapshot_retention_limit  = 7     # 7 days retention for snapshots
snapshot_window           = "00:00-05:00"  # UTC time window for snapshots

# Maintenance and security
maintenance_window        = "sun:05:00-sun:09:00"  # Weekly maintenance window
transit_encryption_enabled = true  # Encryption in transit
at_rest_encryption_enabled = true  # Encryption at rest

# Monitoring thresholds
cpu_threshold    = 75  # Alert at 75% CPU utilization
memory_threshold = 80  # Alert at 80% memory utilization

# Feature flags - all enabled for production
enable_multi_az           = true  # Multi-AZ deployment
enable_automatic_failover = true  # Automatic failover
enable_cluster_mode       = true  # Cluster mode
enable_performance_insights = true  # Performance insights

# Storage Configuration (S3)
# -----------------------------------------------------------------------------
# Region configuration
# Note: Primary region is defined in global settings
replica_region  = "us-west-2"  # Replica region for disaster recovery

# Lifecycle configuration
transition_days = 30  # Transition to IA after 30 days
expiration_days = 0   # No expiration (retain indefinitely for compliance)

# Replication for disaster recovery
enable_replication = true

# Additional tags specific to storage
additional_tags = {
  DataRetention = "Indefinite"
  Compliance    = "MCA-Regulations"
}