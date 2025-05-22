# Development Environment Terraform Variables
# This file contains the actual values for variables defined in variables.tf, specific to the development environment.

# Region Configuration
region = "us-west-2"  # Development region

# General Settings
environment_name = "development"
enable_high_availability = false  # Disable HA for development to reduce costs

# PostgreSQL Configuration
postgresql_instance_type = "db.t3.small"  # Small instance for development
postgresql_storage_gb = 20
postgresql_enable_replicas = false  # No read replicas for development
postgresql_backup_retention_days = 7  # Shorter backup retention for development
postgresql_multi_az = false  # Single AZ deployment for development
postgresql_connection_pool_min = 5
postgresql_connection_pool_max = 20

# RabbitMQ Configuration
rabbitmq_instance_type = "t3.small"  # Small instance for development
rabbitmq_node_count = 1  # Single node for development
rabbitmq_enable_clustering = false  # No clustering for development
rabbitmq_storage_gb = 10
rabbitmq_enable_mirrored_queues = false  # No mirrored queues for development

# Redis Configuration
redis_instance_type = "cache.t3.small"  # Small instance for development
redis_shard_count = 1  # Minimal shards for development
redis_replica_count = 0  # No replicas for development
redis_data_tiering_enabled = false  # Disable data tiering for development
redis_auto_failover = false  # Disable auto-failover for development

# S3 Storage Configuration
s3_bucket_names = {
  documents = "mca-documents-development"
  backups = "mca-backups-development"
}
s3_versioning_enabled = true
s3_lifecycle_rules_enabled = true
s3_encryption_enabled = true  # Keep encryption enabled even in development

# Network Configuration
vpc_cidr = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs = ["10.0.101.0/24", "10.0.102.0/24"]

# Security Configuration
enable_enhanced_monitoring = false  # Disable enhanced monitoring for development
enable_performance_insights = false  # Disable performance insights for development

# Feature Flags
enable_gpu_nodes = false  # Disable GPU nodes for development
enable_auto_scaling = false  # Disable auto-scaling for development

# Kubernetes Configuration
kubernetes_node_instance_type = "t3.medium"  # Small instance for development
kubernetes_node_count = 2  # Minimal node count for development
kubernetes_max_node_count = 3  # Limited auto-scaling for development

# Monitoring Configuration
monitoring_retention_days = 7  # Shorter retention for development
monitoring_alert_emails = ["dev-team@dollarfunding.com"]

# Endpoint Configuration
api_gateway_domain = "api-dev.dollarfunding.com"
frontend_domain = "app-dev.dollarfunding.com"

# Cost Optimization
enable_spot_instances = true  # Use spot instances for development to reduce costs
enable_auto_shutdown = true  # Enable auto-shutdown for development environments during non-business hours
auto_shutdown_start_time = "19:00"  # 7 PM
auto_shutdown_end_time = "07:00"  # 7 AM
auto_shutdown_timezone = "America/Los_Angeles"
auto_shutdown_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]