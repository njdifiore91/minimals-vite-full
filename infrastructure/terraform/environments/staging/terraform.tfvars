# Staging Environment Terraform Variables
# This file contains the actual values for variables defined in variables.tf, specific to the staging environment.
# It configures moderate instance sizes, appropriate high availability features, and staging-specific settings.

# General Settings
environment = "staging"
project_name = "mca"
region = "us-west-2"  # Primary staging region
availability_zones = ["us-west-2a", "us-west-2b"]  # Two AZs for staging
disaster_recovery_region = ""  # No DR region for staging

# Tags
tags = {
  Environment = "staging"
  Project     = "MCA Application Processing"
  ManagedBy   = "Terraform"
  Owner       = "DollarFunding Development"
}

# Database Settings - PostgreSQL 14
database_instance_class = "db.r6g.xlarge"  # Moderate instance for staging workloads
database_allocated_storage = 100  # GB
database_max_allocated_storage = 500  # GB
database_multi_az = true  # Enable multi-AZ deployment for high availability
database_backup_retention_period = 14  # days
database_read_replica_count = 1  # One read replica for staging
database_performance_insights_enabled = true
database_performance_insights_retention_period = 3  # days
database_deletion_protection = false  # Allow deletion for easier management
database_storage_encrypted = true  # Enable encryption at rest
database_monitoring_interval = 60  # seconds, for standard monitoring
database_connection_pool_min = 5
database_connection_pool_max = 25
database_auto_minor_version_upgrade = true
database_maintenance_window = "sun:03:00-sun:05:00"  # Maintenance during low-traffic period
database_backup_window = "01:00-03:00"  # Backup during low-traffic period
database_cross_region_replica_enabled = false  # No cross-region replica for staging

# RabbitMQ Cluster Settings
rabbitmq_instance_type = "r6g.large"  # Smaller instance for staging
rabbitmq_node_count = 3  # 3-node cluster for high availability
rabbitmq_disk_size = 50  # GB
rabbitmq_message_persistence = true  # Enable message persistence
rabbitmq_mirrored_queues = true  # Enable mirrored queues for redundancy
rabbitmq_maintenance_window = "sun:05:00-sun:07:00"  # Maintenance during low-traffic period
rabbitmq_auto_minor_version_upgrade = true
rabbitmq_monitoring_interval = 60  # seconds
rabbitmq_deletion_protection = false  # Allow deletion for easier management

# Redis Cache Settings
redis_instance_type = "cache.r6g.large"  # Smaller instance for staging
redis_cluster_mode_enabled = true  # Enable cluster mode
redis_shard_count = 2  # Fewer shards for staging
redis_replicas_per_shard = 1  # One replica per shard for redundancy
redis_automatic_failover_enabled = true  # Enable automatic failover
redis_maintenance_window = "sun:07:00-sun:09:00"  # Maintenance during low-traffic period
redis_snapshot_retention_limit = 3  # days
redis_snapshot_window = "03:00-05:00"  # Snapshot during low-traffic period
redis_transit_encryption_enabled = true  # Enable encryption in transit
redis_at_rest_encryption_enabled = true  # Enable encryption at rest
redis_auto_minor_version_upgrade = true

# S3 Storage Settings
storage_bucket_name = "mca-documents-staging"  # Staging bucket name
storage_versioning_enabled = true  # Enable versioning for document history
storage_server_side_encryption = "AES256"  # Enable AES-256 encryption
storage_lifecycle_rules_enabled = true  # Enable lifecycle rules
storage_standard_ia_transition_days = 90  # Transition to IA after 90 days
storage_glacier_transition_days = 365  # Transition to Glacier after 365 days
storage_expiration_days = 1825  # Expire objects after 5 years (shorter than production)
storage_cross_region_replication_enabled = false  # No cross-region replication for staging
storage_replication_region = ""  # No replication region
storage_public_access_blocked = true  # Block all public access

# Kubernetes Cluster Settings
kubernetes_cluster_version = "1.25"  # Kubernetes version
kubernetes_node_group_instance_types = {
  "general" = ["m6g.xlarge"],  # Smaller general purpose nodes
  "compute" = ["c6g.2xlarge"],  # Smaller compute-optimized nodes
  "memory"  = ["r6g.xlarge"],  # Smaller memory-optimized nodes
  "gpu"     = ["g4dn.xlarge"]   # Same GPU nodes for OCR processing
}
kubernetes_node_group_desired_sizes = {
  "general" = 2,  # Fewer nodes for staging
  "compute" = 2,  # Fewer compute nodes
  "memory"  = 1,  # Fewer memory nodes
  "gpu"     = 1   # Fewer GPU nodes
}
kubernetes_node_group_min_sizes = {
  "general" = 2,
  "compute" = 1,
  "memory"  = 1,
  "gpu"     = 1
}
kubernetes_node_group_max_sizes = {
  "general" = 4,
  "compute" = 4,
  "memory"  = 2,
  "gpu"     = 2
}
kubernetes_cluster_logging_types = ["api", "audit"]  # Fewer log types for staging
kubernetes_cluster_endpoint_private_access = true  # Enable private access to cluster endpoint
kubernetes_cluster_endpoint_public_access = true   # Enable public access for easier development
kubernetes_cluster_encryption_config_enabled = true  # Enable encryption for secrets

# Monitoring Settings
monitoring_provider = "datadog"  # Use Datadog for monitoring
monitoring_log_retention_days = 14  # days (shorter than production)
monitoring_metrics_retention_months = 6  # months (shorter than production)
monitoring_apm_enabled = true  # Enable application performance monitoring
monitoring_log_level = "DEBUG"  # More verbose logging for staging
monitoring_alert_endpoints = ["dev-alerts@dollarfunding.com"]
monitoring_dashboard_enabled = true

# Network Settings
vpc_cidr = "10.1.0.0/16"  # VPC CIDR block for staging
private_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24"]  # Private subnet CIDR blocks
public_subnet_cidrs = ["10.1.101.0/24", "10.1.102.0/24"]  # Public subnet CIDR blocks
database_subnet_cidrs = ["10.1.201.0/24", "10.1.202.0/24"]  # Database subnet CIDR blocks
nat_gateway_count = 2  # One NAT gateway per AZ

# Security Settings
ssl_certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890"  # SSL certificate ARN
waf_enabled = true  # Enable WAF for API Gateway
shield_advanced_enabled = false  # No Shield Advanced for staging
bastion_enabled = true  # Enable bastion host for secure SSH access
bastion_instance_type = "t4g.small"  # Instance type for bastion host

# Disaster Recovery Settings
dr_enabled = false  # No disaster recovery for staging
dr_rpo_minutes = 0  # N/A
dr_rto_minutes = 0  # N/A
dr_backup_frequency_hours = 12  # Less frequent backups for staging
dr_backup_retention_days = 14  # Shorter backup retention for staging

# Feature Flags
feature_flags_enabled = true  # Enable feature flags for testing
feature_flags_service = "launchdarkly"  # Use LaunchDarkly for feature flags

# API Gateway Settings
api_gateway_type = "regional"  # Regional API Gateway
api_gateway_logging_level = "DEBUG"  # More verbose logging for staging
api_gateway_metrics_enabled = true  # Enable metrics
api_gateway_tracing_enabled = true  # Enable X-Ray tracing
api_gateway_throttling_rate_limit = 500  # Lower rate limit for staging
api_gateway_throttling_burst_limit = 1000  # Lower burst limit for staging
api_gateway_cache_enabled = true  # Enable caching
api_gateway_cache_size = "0.5"  # Smaller cache size for staging