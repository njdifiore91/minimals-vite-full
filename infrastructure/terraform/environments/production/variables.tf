# Variables for the MCA Application Processing System - Production Environment

variable "aws_region" {
  description = "The AWS region to deploy the production infrastructure"
  type        = string
  default     = "us-east-1"  # Default region, can be overridden in terraform.tfvars
}

variable "replica_region" {
  description = "The AWS region for replica resources (disaster recovery)"
  type        = string
  default     = "us-west-2"  # Default replica region, can be overridden in terraform.tfvars
}

variable "aws_account_id" {
  description = "The AWS account ID"
  type        = string
  # No default value for security reasons, must be provided via terraform.tfvars or environment variables
}

variable "domain_name" {
  description = "The domain name for the MCA Application Processing System"
  type        = string
  default     = "dollarfunding.com"
}

variable "cluster_name" {
  description = "The name of the Kubernetes cluster"
  type        = string
  default     = "mca-production"
}

variable "kubernetes_config_path" {
  description = "Path to the Kubernetes config file"
  type        = string
  default     = "~/.kube/config"
}

variable "kubernetes_config_context" {
  description = "Kubernetes config context to use"
  type        = string
  default     = "mca-production"
}

variable "grafana_admin_password" {
  description = "Admin password for Grafana"
  type        = string
  sensitive   = true
  # No default value for security reasons, must be provided via terraform.tfvars or environment variables
}

# Database variables
variable "db_name" {
  description = "The name of the PostgreSQL database"
  type        = string
  default     = "mca_production"
}

variable "db_username" {
  description = "The username for the PostgreSQL database"
  type        = string
  default     = "mca_admin"  # Should be overridden in terraform.tfvars or through environment variables
  sensitive   = true
}

variable "db_password" {
  description = "The password for the PostgreSQL database"
  type        = string
  sensitive   = true
  # No default value for security reasons, must be provided via terraform.tfvars or environment variables
}

# RabbitMQ variables
variable "rabbitmq_username" {
  description = "The username for RabbitMQ"
  type        = string
  default     = "mca_admin"  # Should be overridden in terraform.tfvars or through environment variables
  sensitive   = true
}

variable "rabbitmq_password" {
  description = "The password for RabbitMQ"
  type        = string
  sensitive   = true
  # No default value for security reasons, must be provided via terraform.tfvars or environment variables
}

# Redis variables
variable "redis_auth_token" {
  description = "The authentication token for Redis"
  type        = string
  sensitive   = true
  # No default value for security reasons, must be provided via terraform.tfvars or environment variables
}

# S3 variables
variable "s3_force_destroy" {
  description = "Whether to force destroy S3 buckets even if they contain objects"
  type        = bool
  default     = false  # Default to false for production to prevent accidental data loss
}

# Monitoring variables
variable "enable_enhanced_monitoring" {
  description = "Whether to enable enhanced monitoring for database instances"
  type        = bool
  default     = true
}

variable "monitoring_interval_seconds" {
  description = "The interval in seconds between points when Enhanced Monitoring metrics are collected"
  type        = number
  default     = 15
}

# High availability variables
variable "multi_az_enabled" {
  description = "Whether to enable Multi-AZ deployment for high availability"
  type        = bool
  default     = true  # Default to true for production
}

# Backup variables
variable "backup_window" {
  description = "The daily time range during which automated backups are created"
  type        = string
  default     = "03:00-05:00"  # 3-5 AM UTC
}

variable "maintenance_window" {
  description = "The weekly time range during which system maintenance can occur"
  type        = string
  default     = "sun:05:00-sun:07:00"  # Sunday 5-7 AM UTC
}

# Security variables
variable "enable_encryption" {
  description = "Whether to enable encryption for data at rest"
  type        = bool
  default     = true
}

variable "enable_deletion_protection" {
  description = "Whether to enable deletion protection for database instances"
  type        = bool
  default     = true  # Default to true for production
}

# Performance variables
variable "enable_performance_insights" {
  description = "Whether to enable Performance Insights for database instances"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "The retention period for Performance Insights data in days"
  type        = number
  default     = 7  # 7 days retention
}

# Network variables
variable "vpc_id" {
  description = "The ID of the VPC where resources will be deployed"
  type        = string
  # No default value, must be provided via terraform.tfvars or environment variables
}

variable "subnet_ids" {
  description = "The IDs of the subnets where resources will be deployed"
  type        = list(string)
  # No default value, must be provided via terraform.tfvars or environment variables
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}