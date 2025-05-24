# Staging Environment Terraform Variables
# This file contains the actual values for variables defined in variables.tf, specific to the staging environment.
# It configures moderate instance sizes, high availability features, and staging-specific settings.

# General Settings
environment = "staging"
project_name = "mca"
aws_region = "us-east-1"  # Primary staging region
replica_region = "us-west-2"  # Secondary region for disaster recovery testing
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]  # Multiple AZs for high availability

# Tags
additional_tags = {
  Environment = "Staging"
  Project     = "MCA Application Processing"
  ManagedBy   = "Terraform"
  Owner       = "DollarFunding Operations"
  CostCenter  = "MCA-002"
}

# Database Settings - PostgreSQL 14
db_name = "mca_staging"
# db_username and db_password should be provided via environment variables or secure secrets management
db_instance_class = "db.r6g.xlarge"  # Moderate instance for staging workloads
db_allocated_storage = 200  # GB
db_max_allocated_storage = 500  # GB
multi_az_enabled = true  # Enable multi-AZ deployment for high availability
backup_retention_period = 14  # days
db_replica_count = 1  # One read replica for staging (as specified in the technical spec)
enable_performance_insights = true
performance_insights_retention_period = 7  # days
enable_deletion_protection = false  # Allow deletion for easier environment management
enable_encryption = true  # Enable encryption at rest
monitoring_interval_seconds = 15  # seconds, for enhanced monitoring
enable_enhanced_monitoring = true
db_connection_pool_min = 10
db_connection_pool_max = 50
db_auto_minor_version_upgrade = true
maintenance_window = "sun:03:00-sun:05:00"  # Maintenance during low-traffic period
backup_window = "01:00-03:00"  # Backup during low-traffic period
db_cross_region_replica_enabled = false  # No cross-region replica for staging

# RabbitMQ Cluster Settings
rabbitmq_instance_type = "r6g.large"  # Moderate instance for staging
rabbitmq_node_count = 3  # 3-node cluster for high availability
rabbitmq_disk_size = 50  # GB
rabbitmq_message_persistence = true  # Enable message persistence
rabbitmq_mirrored_queues = true  # Enable mirrored queues for redundancy
rabbitmq_maintenance_window = "sun:05:00-sun:07:00"  # Maintenance during low-traffic period
rabbitmq_auto_minor_version_upgrade = true
rabbitmq_monitoring_interval = 15  # seconds
rabbitmq_deletion_protection = false  # Allow deletion for easier environment management
rabbitmq_exchanges = ["mca.documents"]  # Fanout exchange
rabbitmq_queues = ["document-processing", "data-extraction", "notification"]

# Redis Cache Settings
redis_instance_type = "cache.r6g.large"  # Moderate instance for staging
redis_cluster_mode_enabled = true  # Enable cluster mode
redis_shard_count = 2  # Number of shards (less than production)
redis_replicas_per_shard = 1  # One replica per shard for redundancy
redis_automatic_failover_enabled = true  # Enable automatic failover
redis_maintenance_window = "sun:07:00-sun:09:00"  # Maintenance during low-traffic period
redis_snapshot_retention_limit = 7  # days
redis_snapshot_window = "03:00-05:00"  # Snapshot during low-traffic period
redis_transit_encryption_enabled = true  # Enable encryption in transit
redis_at_rest_encryption_enabled = true  # Enable encryption at rest
redis_auto_minor_version_upgrade = true
redis_data_ttl = 15  # Minutes for application data (same as other environments)
redis_session_ttl = 1440  # Minutes (24 hours) for user sessions (same as other environments)

# S3 Storage Settings
s3_bucket_name = "mca-documents-staging"  # Staging bucket name
s3_force_destroy = true  # Allow bucket destruction with objects for easier environment management
s3_versioning_enabled = true  # Enable versioning for document history
s3_encryption_enabled = true  # Enable AES-256 encryption
s3_lifecycle_rules_enabled = true  # Enable lifecycle rules
s3_standard_ia_transition_days = 90  # Transition to IA after 90 days
s3_glacier_transition_days = 365  # Transition to Glacier after 365 days
s3_expiration_days = 2555  # Expire objects after 7 years (compliance requirement)
s3_cross_region_replication_enabled = false  # No cross-region replication for staging
s3_public_access_blocked = true  # Block all public access

# Kubernetes Cluster Settings
kubernetes_cluster_version = "1.25"  # Kubernetes version
kubernetes_node_group_instance_types = {
  "general" = ["m6g.xlarge"],   # General purpose nodes (smaller than production)
  "compute" = ["c6g.2xlarge"],  # Compute-optimized nodes for data processing
  "memory"  = ["r6g.xlarge"],   # Memory-optimized nodes for caching
  "gpu"     = ["g4dn.xlarge"]   # GPU nodes for OCR processing
}
kubernetes_node_group_desired_sizes = {
  "general" = 2,  # Fewer nodes than production
  "compute" = 2,  # Compute nodes for data processing
  "memory"  = 1,  # Memory nodes for caching
  "gpu"     = 1   # GPU nodes for OCR processing
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
kubernetes_cluster_logging_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
kubernetes_cluster_endpoint_private_access = true  # Enable private access to cluster endpoint
kubernetes_cluster_endpoint_public_access = true   # Enable public access for easier testing in staging
kubernetes_cluster_encryption_config_enabled = true  # Enable encryption for secrets

# Monitoring Settings
monitoring_provider = "datadog"  # Use Datadog for monitoring
monitoring_log_retention_days = 14  # days (less than production)
monitoring_metrics_retention_months = 6  # months (less than production)
monitoring_apm_enabled = true  # Enable application performance monitoring
monitoring_log_level = "INFO"  # Default log level for staging
monitoring_alert_endpoints = ["staging-alerts@dollarfunding.com"]
monitoring_dashboard_enabled = true

# Network Settings
vpc_cidr = "10.1.0.0/16"  # VPC CIDR block for staging
private_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]  # Private subnet CIDR blocks
public_subnet_cidrs = ["10.1.101.0/24", "10.1.102.0/24", "10.1.103.0/24"]  # Public subnet CIDR blocks
database_subnet_cidrs = ["10.1.201.0/24", "10.1.202.0/24", "10.1.203.0/24"]  # Database subnet CIDR blocks
nat_gateway_count = 2  # Fewer NAT gateways than production for cost savings

# Security Settings
ssl_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/abcdef12-3456-7890-abcd-ef1234567890"  # SSL certificate ARN
waf_enabled = true  # Enable WAF for API Gateway
shield_advanced_enabled = false  # No Shield Advanced for staging
bastion_enabled = true  # Enable bastion host for secure SSH access
bastion_instance_type = "t4g.small"  # Instance type for bastion host

# Disaster Recovery Settings
dr_enabled = false  # No disaster recovery for staging
dr_rpo_minutes = 15  # Recovery Point Objective in minutes (for configuration compatibility)
dr_rto_minutes = 30  # Recovery Time Objective in minutes (for configuration compatibility)
dr_backup_frequency_hours = 12  # Backup frequency in hours
dr_backup_retention_days = 14  # Backup retention in days

# Feature Flags
feature_flags_enabled = true  # Enable feature flags for testing
feature_flags_service = "launchdarkly"  # Use LaunchDarkly for feature flags

# API Gateway Settings
api_gateway_type = "regional"  # Regional API Gateway
api_gateway_logging_level = "INFO"  # Logging level
api_gateway_metrics_enabled = true  # Enable metrics
api_gateway_tracing_enabled = true  # Enable X-Ray tracing
api_gateway_throttling_rate_limit = 500  # Requests per second (lower than production)
api_gateway_throttling_burst_limit = 1000  # Burst limit (lower than production)
api_gateway_cache_enabled = true  # Enable caching
api_gateway_cache_size = "0.5"  # Cache size in GB (smaller than production)