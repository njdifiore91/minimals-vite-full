# Production Environment Terraform Variables
# This file contains the actual values for variables defined in variables.tf, specific to the production environment.
# It configures large instance sizes, full high availability features, and production-specific settings.

# General Settings
environment = "production"
project_name = "mca"
region = "us-west-2"  # Primary production region
availability_zones = ["us-west-2a", "us-west-2b", "us-west-2c"]  # Multiple AZs for high availability
disaster_recovery_region = "us-east-1"  # Secondary region for disaster recovery

# Tags
tags = {
  Environment = "production"
  Project     = "MCA Application Processing"
  ManagedBy   = "Terraform"
  Owner       = "DollarFunding Operations"
}

# Database Settings - PostgreSQL 14
database_instance_class = "db.r6g.2xlarge"  # Large instance for production workloads
database_allocated_storage = 500  # GB
database_max_allocated_storage = 1000  # GB
database_multi_az = true  # Enable multi-AZ deployment for high availability
database_backup_retention_period = 30  # days
database_read_replica_count = 2  # Two read replicas for production
database_performance_insights_enabled = true
database_performance_insights_retention_period = 7  # days
database_deletion_protection = true  # Prevent accidental deletion
database_storage_encrypted = true  # Enable encryption at rest
database_monitoring_interval = 15  # seconds, for enhanced monitoring
database_connection_pool_min = 10
database_connection_pool_max = 50
database_auto_minor_version_upgrade = true
database_maintenance_window = "sun:03:00-sun:05:00"  # Maintenance during low-traffic period
database_backup_window = "01:00-03:00"  # Backup during low-traffic period
database_cross_region_replica_enabled = true  # Enable cross-region replica for disaster recovery

# RabbitMQ Cluster Settings
rabbitmq_instance_type = "r6g.xlarge"  # Memory-optimized instance for message processing
rabbitmq_node_count = 3  # 3-node cluster for high availability
rabbitmq_disk_size = 100  # GB
rabbitmq_message_persistence = true  # Enable message persistence
rabbitmq_mirrored_queues = true  # Enable mirrored queues for redundancy
rabbitmq_maintenance_window = "sun:05:00-sun:07:00"  # Maintenance during low-traffic period
rabbitmq_auto_minor_version_upgrade = true
rabbitmq_monitoring_interval = 15  # seconds
rabbitmq_deletion_protection = true  # Prevent accidental deletion

# Redis Cache Settings
redis_instance_type = "cache.r6g.xlarge"  # Memory-optimized instance for caching
redis_cluster_mode_enabled = true  # Enable cluster mode
redis_shard_count = 3  # Number of shards
redis_replicas_per_shard = 1  # One replica per shard for redundancy
redis_automatic_failover_enabled = true  # Enable automatic failover
redis_maintenance_window = "sun:07:00-sun:09:00"  # Maintenance during low-traffic period
redis_snapshot_retention_limit = 7  # days
redis_snapshot_window = "03:00-05:00"  # Snapshot during low-traffic period
redis_transit_encryption_enabled = true  # Enable encryption in transit
redis_at_rest_encryption_enabled = true  # Enable encryption at rest
redis_auto_minor_version_upgrade = true

# S3 Storage Settings
storage_bucket_name = "mca-documents-production"  # Production bucket name
storage_versioning_enabled = true  # Enable versioning for document history
storage_server_side_encryption = "AES256"  # Enable AES-256 encryption
storage_lifecycle_rules_enabled = true  # Enable lifecycle rules
storage_standard_ia_transition_days = 90  # Transition to IA after 90 days
storage_glacier_transition_days = 365  # Transition to Glacier after 365 days
storage_expiration_days = 2555  # Expire objects after 7 years (compliance requirement)
storage_cross_region_replication_enabled = true  # Enable cross-region replication
storage_replication_region = "us-east-1"  # Replicate to disaster recovery region
storage_public_access_blocked = true  # Block all public access

# Kubernetes Cluster Settings
kubernetes_cluster_version = "1.25"  # Kubernetes version
kubernetes_node_group_instance_types = {
  "general" = ["m6g.2xlarge"],  # General purpose nodes
  "compute" = ["c6g.4xlarge"],  # Compute-optimized nodes for data processing
  "memory"  = ["r6g.2xlarge"],  # Memory-optimized nodes for caching
  "gpu"     = ["g4dn.xlarge"]   # GPU nodes for OCR processing
}
kubernetes_node_group_desired_sizes = {
  "general" = 3,  # Minimum 3 nodes for high availability
  "compute" = 4,  # Compute nodes for data processing
  "memory"  = 2,  # Memory nodes for caching
  "gpu"     = 2   # GPU nodes for OCR processing
}
kubernetes_node_group_min_sizes = {
  "general" = 3,
  "compute" = 2,
  "memory"  = 2,
  "gpu"     = 1
}
kubernetes_node_group_max_sizes = {
  "general" = 6,
  "compute" = 8,
  "memory"  = 4,
  "gpu"     = 4
}
kubernetes_cluster_logging_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
kubernetes_cluster_endpoint_private_access = true  # Enable private access to cluster endpoint
kubernetes_cluster_endpoint_public_access = false  # Disable public access to cluster endpoint
kubernetes_cluster_encryption_config_enabled = true  # Enable encryption for secrets

# Monitoring Settings
monitoring_provider = "datadog"  # Use Datadog for monitoring
monitoring_log_retention_days = 30  # days
monitoring_metrics_retention_months = 15  # months
monitoring_apm_enabled = true  # Enable application performance monitoring
monitoring_log_level = "INFO"  # Default log level for production
monitoring_alert_endpoints = ["ops@dollarfunding.com", "tech-alerts@dollarfunding.com"]
monitoring_dashboard_enabled = true

# Network Settings
vpc_cidr = "10.0.0.0/16"  # VPC CIDR block
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]  # Private subnet CIDR blocks
public_subnet_cidrs = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]  # Public subnet CIDR blocks
database_subnet_cidrs = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]  # Database subnet CIDR blocks
nat_gateway_count = 3  # One NAT gateway per AZ for high availability

# Security Settings
ssl_certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890"  # SSL certificate ARN
waf_enabled = true  # Enable WAF for API Gateway
shield_advanced_enabled = true  # Enable Shield Advanced for DDoS protection
bastion_enabled = true  # Enable bastion host for secure SSH access
bastion_instance_type = "t4g.small"  # Instance type for bastion host

# Disaster Recovery Settings
dr_enabled = true  # Enable disaster recovery
dr_rpo_minutes = 15  # Recovery Point Objective in minutes
dr_rto_minutes = 30  # Recovery Time Objective in minutes
dr_backup_frequency_hours = 6  # Backup frequency in hours
dr_backup_retention_days = 30  # Backup retention in days

# Feature Flags
feature_flags_enabled = true  # Enable feature flags for gradual rollout
feature_flags_service = "launchdarkly"  # Use LaunchDarkly for feature flags

# API Gateway Settings
api_gateway_type = "regional"  # Regional API Gateway
api_gateway_logging_level = "INFO"  # Logging level
api_gateway_metrics_enabled = true  # Enable metrics
api_gateway_tracing_enabled = true  # Enable X-Ray tracing
api_gateway_throttling_rate_limit = 1000  # Requests per second
api_gateway_throttling_burst_limit = 2000  # Burst limit
api_gateway_cache_enabled = true  # Enable caching
api_gateway_cache_size = "1.6"  # Cache size in GB