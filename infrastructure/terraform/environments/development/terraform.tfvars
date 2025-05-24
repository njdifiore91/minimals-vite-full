# terraform.tfvars for MCA Application Processing System - Development Environment
# Contains environment-specific variable values for the development infrastructure

# Region configuration
aws_region     = "us-east-1"
replica_region = "us-west-2"  # Not used in development but kept for module compatibility

# Network configuration
vpc_id      = "vpc-dev01234567890"  # Development VPC ID
subnet_ids  = ["subnet-dev0123a", "subnet-dev0123b"]  # Development subnet IDs

# Database configuration
db_name     = "mca_development"
db_username = "mca_dev"
db_password = "Dev_Password_123!"  # Should be replaced with a secure password or secret management

# RabbitMQ configuration
rabbitmq_username = "mca_dev"
rabbitmq_password = "Dev_RabbitMQ_123!"  # Should be replaced with a secure password or secret management

# Redis configuration
redis_auth_token = "Dev_Redis_Token_123!"  # Should be replaced with a secure token or secret management

# S3 configuration
s3_force_destroy = true  # Allow force destroy in development for easier cleanup

# Monitoring configuration - simplified for development
enable_enhanced_monitoring = false
monitoring_interval_seconds = 60  # Less frequent monitoring for development

# High availability configuration - disabled for development
multi_az_enabled = false  # Single AZ for development to reduce costs

# Backup configuration
backup_window = "03:00-05:00"  # 3-5 AM UTC
maintenance_window = "sun:05:00-sun:07:00"  # Sunday 5-7 AM UTC

# Security configuration
enable_encryption = true  # Keep encryption enabled even in development
enable_deletion_protection = false  # No deletion protection for development

# Performance configuration - simplified for development
enable_performance_insights = false
performance_insights_retention_period = 7  # 7 days retention

# Additional tags
additional_tags = {
  Owner       = "Development Team"
  CostCenter  = "DevOps"
  Application = "MCA Processing System"
}