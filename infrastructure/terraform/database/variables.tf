# PostgreSQL Database Variables
# This file defines input variables for the PostgreSQL configuration, including environment-specific settings,
# instance types, storage sizes, backup retention periods, and security parameters.

# Environment Configuration
variable "environment" {
  description = "The environment for which the PostgreSQL database is configured (production, staging, development)"
  type        = string
  default     = "development"
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "The environment must be one of: production, staging, development."
  }
}

variable "region" {
  description = "The AWS region in which to deploy the PostgreSQL database"
  type        = string
  default     = "us-east-1"
}

# Instance Configuration
variable "db_instance_class" {
  description = "The instance type for the primary PostgreSQL database"
  type        = string
  default     = "db.t3.medium"
}

variable "db_replica_instance_class" {
  description = "The instance type for the PostgreSQL read replicas"
  type        = string
  default     = "db.t3.medium"
}

# Storage Configuration
variable "db_allocated_storage" {
  description = "The allocated storage size in GB for the PostgreSQL database"
  type        = number
  default     = 100
  validation {
    condition     = var.db_allocated_storage >= 20 && var.db_allocated_storage <= 16384
    error_message = "The allocated storage must be between 20 and 16384 GB."
  }
}

variable "db_max_allocated_storage" {
  description = "The maximum storage size in GB to which the PostgreSQL database can grow"
  type        = number
  default     = 1000
  validation {
    condition     = var.db_max_allocated_storage >= 20 && var.db_max_allocated_storage <= 16384
    error_message = "The maximum allocated storage must be between 20 and 16384 GB."
  }
}

# Backup Configuration
variable "backup_retention_period" {
  description = "The number of days for which automated backups are retained"
  type        = number
  default     = 30
  validation {
    condition     = var.backup_retention_period >= 0 && var.backup_retention_period <= 35
    error_message = "The backup retention period must be between 0 and 35 days."
  }
}

variable "backup_window" {
  description = "The daily time range during which automated backups are created (in UTC)"
  type        = string
  default     = "03:00-06:00"
}

variable "maintenance_window" {
  description = "The weekly time range during which system maintenance can occur (in UTC)"
  type        = string
  default     = "Mon:00:00-Mon:03:00"
}

# Security Configuration
variable "db_password" {
  description = "The master password for the PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "storage_encrypted" {
  description = "Whether the PostgreSQL database storage should be encrypted"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "The ARN of the KMS key to use for encrypting the PostgreSQL database storage"
  type        = string
  default     = ""
}

variable "vpc_security_group_ids" {
  description = "A list of VPC security group IDs to associate with the PostgreSQL database"
  type        = list(string)
  default     = []
}

variable "subnet_ids" {
  description = "A list of VPC subnet IDs to associate with the PostgreSQL database"
  type        = list(string)
  default     = []
}

# Connection Pooling Configuration
variable "parameter_group_name" {
  description = "The name of the DB parameter group to associate with the PostgreSQL database"
  type        = string
  default     = ""
}

variable "max_connections" {
  description = "The maximum number of connections allowed to the PostgreSQL database"
  type        = number
  default     = 200
  validation {
    condition     = var.max_connections >= 10 && var.max_connections <= 5000
    error_message = "The maximum number of connections must be between 10 and 5000."
  }
}

variable "connection_timeout" {
  description = "The connection timeout in seconds for the PostgreSQL database"
  type        = number
  default     = 30
  validation {
    condition     = var.connection_timeout >= 1 && var.connection_timeout <= 600
    error_message = "The connection timeout must be between 1 and 600 seconds."
  }
}

# Monitoring Configuration
variable "monitoring_interval" {
  description = "The interval, in seconds, between points when Enhanced Monitoring metrics are collected"
  type        = number
  default     = 15
  validation {
    condition     = contains([0, 1, 5, 10, 15, 30, 60], var.monitoring_interval)
    error_message = "The monitoring interval must be one of: 0, 1, 5, 10, 15, 30, 60."
  }
}

variable "monitoring_role_arn" {
  description = "The ARN for the IAM role that permits RDS to send enhanced monitoring metrics to CloudWatch Logs"
  type        = string
  default     = ""
}

variable "performance_insights_enabled" {
  description = "Whether Performance Insights should be enabled for the PostgreSQL database"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "The amount of time in days to retain Performance Insights data"
  type        = number
  default     = 7
  validation {
    condition     = contains([7, 731], var.performance_insights_retention_period) || var.performance_insights_retention_period == 0
    error_message = "The Performance Insights retention period must be either 7 (free tier) or 731 (paid tier) days, or 0 to disable."
  }
}

# High Availability Configuration
variable "multi_az" {
  description = "Whether the PostgreSQL database should be deployed in multiple availability zones"
  type        = bool
  default     = true
}

variable "publicly_accessible" {
  description = "Whether the PostgreSQL database should be publicly accessible"
  type        = bool
  default     = false
}

# Advanced Configuration
variable "apply_immediately" {
  description = "Whether any database modifications should be applied immediately, or during the next maintenance window"
  type        = bool
  default     = false
}

variable "auto_minor_version_upgrade" {
  description = "Whether minor engine upgrades will be applied automatically to the PostgreSQL database during the maintenance window"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Whether the PostgreSQL database should have deletion protection enabled"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Whether a final DB snapshot should be created before the PostgreSQL database is deleted"
  type        = bool
  default     = false
}

variable "final_snapshot_identifier_prefix" {
  description = "The prefix for the name of the final DB snapshot when the PostgreSQL database is deleted"
  type        = string
  default     = "final-snapshot"
}

# Tags
variable "tags" {
  description = "A map of tags to assign to the PostgreSQL database resources"
  type        = map(string)
  default     = {}
}