# Variables for RabbitMQ Messaging Module
#
# This file defines all input variables for the RabbitMQ messaging module,
# including environment type, instance sizes, storage configurations, and feature flags.
# These variables enable flexible and reusable messaging infrastructure deployment
# across different environments.

# Environment variables
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

# AWS region for deployment
variable "aws_region" {
  description = "AWS region for RabbitMQ cluster deployment"
  type        = string
  default     = "us-east-1"
}

# Instance type based on environment
variable "instance_type" {
  description = "RabbitMQ broker instance type"
  type        = string
  default     = "mq.m5.large"
}

# Network configuration
variable "subnet_ids" {
  description = "List of subnet IDs for RabbitMQ deployment (minimum 3 for multi-AZ)"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for RabbitMQ cluster"
  type        = string
}

# RabbitMQ configuration
variable "rabbitmq_admin_username" {
  description = "Username for RabbitMQ admin user"
  type        = string
  default     = "admin"
}

variable "rabbitmq_admin_password" {
  description = "Password for RabbitMQ admin user"
  type        = string
  sensitive   = true
}

variable "rabbitmq_vhost" {
  description = "RabbitMQ virtual host"
  type        = string
  default     = "/"
}

# Maintenance window configuration
variable "maintenance_day_of_week" {
  description = "Day of week for maintenance window"
  type        = string
  default     = "SUNDAY"
}

variable "maintenance_time_of_day" {
  description = "Time of day for maintenance window (UTC)"
  type        = string
  default     = "03:00"
}

variable "maintenance_time_zone" {
  description = "Time zone for maintenance window"
  type        = string
  default     = "UTC"
}

# Monitoring configuration
variable "alarm_actions" {
  description = "List of ARNs to notify when alarm transitions to ALARM state"
  type        = list(string)
  default     = []
}

variable "ok_actions" {
  description = "List of ARNs to notify when alarm transitions to OK state"
  type        = list(string)
  default     = []
}

variable "critical_queues" {
  description = "List of critical queue names to monitor"
  type        = list(string)
  default     = ["document-processing", "data-extraction", "notification"]
}

variable "queue_depth_threshold" {
  description = "Threshold for queue depth alarm"
  type        = number
  default     = 10000
}

# DNS configuration
variable "create_dns_record" {
  description = "Whether to create a DNS record for the RabbitMQ cluster"
  type        = bool
  default     = false
}

variable "dns_zone_id" {
  description = "Route53 hosted zone ID for DNS record"
  type        = string
  default     = ""
}

variable "dns_domain" {
  description = "Domain name for RabbitMQ DNS record"
  type        = string
  default     = ""
}

# Common tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}