# Variable values for the MCA Application Processing System - Development Environment

# Region configuration
aws_region     = "us-east-2"  # Development region
replica_region = "us-west-1"  # Not used in development but kept for module compatibility

# Database configuration - PostgreSQL 14
db_name = "mca_development"
# db_username and db_password should be provided via environment variables or secure secrets management
db_instance_class = "db.t3.micro"  # Smallest instance size for development
db_allocated_storage = 20  # GB
db_max_allocated_storage = 50  # GB
db_replica_count = 0  # No read replicas for development

# RabbitMQ configuration
rabbitmq_instance_type = "t3.micro"  # Smallest instance size for development
rabbitmq_node_count = 1  # Single node for development
rabbitmq_exchanges = ["mca.documents"]  # Fanout exchange
rabbitmq_queues = ["document-processing", "data-extraction", "notification"]

# Redis configuration
redis_instance_type = "cache.t3.micro"  # Smallest instance size for development
redis_node_count = 1  # Single node for development
redis_data_ttl = 15  # Minutes for application data (same as other environments)
redis_session_ttl = 1440  # Minutes (24 hours) for user sessions (same as other environments)

# S3 Storage configuration
s3_bucket_name = "mca-documents-development"  # Development-specific bucket name
s3_versioning_enabled = true
s3_encryption_enabled = true  # AES-256 encryption

# Network configuration
# These values would be specific to your AWS account and VPC setup
# vpc_id = "vpc-0123456789abcdef0"
# subnet_ids = ["subnet-0123456789abcdef0"]

# High availability configuration
multi_az_enabled = false  # No high availability for development

# Backup configuration
backup_window      = "02:00-04:00"  # 2-4 AM UTC
maintenance_window = "sun:04:00-sun:06:00"  # Sunday 4-6 AM UTC
backup_retention_period = 7  # Days (shorter for development)

# Security configuration
enable_encryption = true  # Keep encryption enabled even in development
enable_deletion_protection = false  # No deletion protection for development

# Monitoring configuration
enable_enhanced_monitoring = false  # Basic monitoring for development
monitoring_interval_seconds = 60  # Less frequent for development
enable_performance_insights = false  # No performance insights for development
performance_insights_retention_period = 7  # Days

# Kubernetes configuration
k8s_node_instance_type = "t3.small"  # Smallest instance size for development
k8s_node_count_min = 1  # Minimum nodes
k8s_node_count_max = 3  # Maximum nodes for auto-scaling

# GPU configuration for OCR service
gpu_enabled = false  # No GPU for development environment
gpu_instance_type = ""  # No GPU instance type needed

# Additional tags
additional_tags = {
  Environment  = "Development"
  BusinessUnit = "Funding"
  CostCenter   = "MCA-003"
  Owner        = "developers@dollarfunding.com"
}