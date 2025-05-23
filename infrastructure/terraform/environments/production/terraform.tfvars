# Variable values for the MCA Application Processing System - Production Environment

# Region configuration
aws_region     = "us-east-1"  # Primary region
replica_region = "us-west-2"  # Replica region for disaster recovery

# AWS account configuration
# aws_account_id = "123456789012"  # Should be provided via environment variables or secure secrets management

# Domain configuration
domain_name = "dollarfunding.com"

# Kubernetes configuration
cluster_name = "mca-production"
# kubernetes_config_path = "~/.kube/config"  # Should be provided via environment variables or secure secrets management
# kubernetes_config_context = "mca-production"  # Should be provided via environment variables or secure secrets management

# Grafana configuration
# grafana_admin_password should be provided via environment variables or secure secrets management

# Database configuration
db_name = "mca_production"
# db_username and db_password should be provided via environment variables or secure secrets management

# Network configuration
# These values would be specific to your AWS account and VPC setup
# vpc_id = "vpc-0123456789abcdef0"
# subnet_ids = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1", "subnet-0123456789abcdef2"]

# High availability configuration
multi_az_enabled = true

# Backup configuration
backup_window      = "03:00-05:00"  # 3-5 AM UTC
maintenance_window = "sun:05:00-sun:07:00"  # Sunday 5-7 AM UTC

# Security configuration
enable_encryption        = true
enable_deletion_protection = true

# Monitoring configuration
enable_enhanced_monitoring = true
monitoring_interval_seconds = 15
enable_performance_insights = true
performance_insights_retention_period = 7

# Additional tags
additional_tags = {
  BusinessUnit = "Funding"
  CostCenter   = "MCA-001"
  Owner        = "operations@dollarfunding.com"
}