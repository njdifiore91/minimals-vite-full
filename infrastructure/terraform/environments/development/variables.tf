# Variables for the MCA Application Processing System - Development Environment

variable "aws_region" {
  description = "The AWS region to deploy the development infrastructure"
  type        = string
  default     = "us-east-1"  # Default region, can be overridden in terraform.tfvars
}

variable "replica_region" {
  description = "The AWS region for replica resources (not used in development)"
  type        = string
  default     = "us-west-2"  # Not used in development but kept for module compatibility
}

# Database variables
variable "db_name" {
  description = "The name of the PostgreSQL database"
  type        = string
  default     = "mca_development"
}

variable "db_username" {
  description = "The username for the PostgreSQL database"
  type        = string
  default     = "mca_dev"  # Should be overridden in terraform.tfvars or through environment variables
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
  default     = "mca_dev"  # Should be overridden in terraform.tfvars or through environment variables
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
  default     = true  # Default to true for development to allow easier cleanup
}

# Monitoring variables
variable "enable_enhanced_monitoring" {
  description = "Whether to enable enhanced monitoring for database instances"
  type        = bool
  default     = false  # Simplified monitoring for development
}

variable "monitoring_interval_seconds" {
  description = "The interval in seconds between points when Enhanced Monitoring metrics are collected"
  type        = number
  default     = 60  # Less frequent monitoring for development
}

# High availability variables
variable "multi_az_enabled" {
  description = "Whether to enable Multi-AZ deployment for high availability"
  type        = bool
  default     = false  # Single AZ for development
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
  default     = true  # Keep encryption enabled even in development
}

variable "enable_deletion_protection" {
  description = "Whether to enable deletion protection for database instances"
  type        = bool
  default     = false  # No deletion protection for development
}

# Performance variables
variable "enable_performance_insights" {
  description = "Whether to enable Performance Insights for database instances"
  type        = bool
  default     = false  # Simplified performance monitoring for development
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