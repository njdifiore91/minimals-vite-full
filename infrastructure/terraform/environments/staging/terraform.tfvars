# Variable values for the MCA Application Processing System - Staging Environment

# Region configuration
aws_region     = "us-east-2"  # Staging region
replica_region = "us-west-1"  # Replica region for staging

# Database configuration - PostgreSQL 14
db_name = "mca_staging"
# db_username and db_password should be provided via environment variables or secure secrets management
db_instance_class = "db.t3.medium"  # Moderate instance size for staging
db_allocated_storage = 50  # GB
db_max_allocated_storage = 100  # GB
db_replica_count = 1  # One read replica for staging (vs 2 for production)

# RabbitMQ configuration
rabbitmq_instance_type = "t3.small"  # Moderate instance size for staging
rabbitmq_node_count = 3  # Minimum for high availability
rabbitmq_exchanges = ["mca.documents"]  # Fanout exchange
rabbitmq_queues = ["document-processing", "data-extraction", "notification"]

# Redis configuration
redis_instance_type = "cache.t3.small"  # Moderate instance size for staging
redis_node_count = 3  # Minimum for high availability
redis_data_ttl = 15  # Minutes for application data
redis_session_ttl = 1440  # Minutes (24 hours) for user sessions

# S3 Storage configuration
s3_bucket_name = "mca-documents-staging"  # Staging-specific bucket name
s3_versioning_enabled = true
s3_encryption_enabled = true  # AES-256 encryption

# Network configuration
# These values would be specific to your AWS account and VPC setup
# vpc_id = "vpc-0123456789abcdef0"
# subnet_ids = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1", "subnet-0123456789abcdef2"]

# High availability configuration
multi_az_enabled = true  # Enable high availability for staging

# Backup configuration
backup_window      = "02:00-04:00"  # 2-4 AM UTC
maintenance_window = "sun:04:00-sun:06:00"  # Sunday 4-6 AM UTC
backup_retention_period = 14  # Days

# Security configuration
enable_encryption = true
enable_deletion_protection = true

# Monitoring configuration
enable_enhanced_monitoring = true
monitoring_interval_seconds = 30  # Less frequent than production (15s)
enable_performance_insights = true
performance_insights_retention_period = 7  # Days

# Kubernetes configuration
k8s_node_instance_type = "t3.medium"  # Moderate instance size for staging
k8s_node_count_min = 2  # Minimum nodes
k8s_node_count_max = 5  # Maximum nodes for auto-scaling

# GPU configuration for OCR service
gpu_enabled = true
gpu_instance_type = "g4dn.xlarge"  # Smaller GPU instance for staging

# Additional tags
additional_tags = {
  Environment  = "Staging"
  BusinessUnit = "Funding"
  CostCenter   = "MCA-002"
  Owner        = "devops@dollarfunding.com"
}