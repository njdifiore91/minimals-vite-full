# PostgreSQL Database Module Variables
# This module configures PostgreSQL 14 database instances with read replicas
# according to the MCA Application Processing System requirements

variable "environment" {
  description = "Environment name (production, staging, development) - determines replica count and other environment-specific settings"
  type        = string
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development."
  }
}

# Instance Configuration
variable "instance_class" {
  description = "The instance type of the RDS instance - should be sized appropriately for the environment"
  type        = string
  default     = "db.t3.medium"
}

variable "allocated_storage" {
  description = "The allocated storage in gigabytes for the PostgreSQL instance"
  type        = number
  default     = 100
  validation {
    condition     = var.allocated_storage >= 20
    error_message = "Allocated storage must be at least 20GB."
  }
}

variable "max_allocated_storage" {
  description = "The upper limit to which Amazon RDS can automatically scale the storage of the DB instance"
  type        = number
  default     = 1000
  validation {
    condition     = var.max_allocated_storage >= 100
    error_message = "Maximum allocated storage must be at least 100GB."
  }
}

variable "storage_type" {
  description = "Storage type for the database. General purpose SSD with 1000 IOPS baseline is recommended"
  type        = string
  default     = "gp2" # General purpose SSD as specified in requirements
  validation {
    condition     = contains(["standard", "gp2", "gp3", "io1"], var.storage_type)
    error_message = "Storage type must be one of: standard, gp2, gp3, io1."
  }
}

variable "iops" {
  description = "The amount of provisioned IOPS. Only applicable if storage_type is 'io1' or 'gp3'. Baseline of 1000 IOPS is recommended"
  type        = number
  default     = 1000 # As specified in requirements
  validation {
    condition     = var.iops >= 1000
    error_message = "IOPS must be at least 1000 as per requirements."
  }
}

# Replica Configuration
variable "replica_count" {
  description = "Number of read replicas to create (2 for production, 1 for staging, 0 for development)"
  type        = number
  default     = 0
  validation {
    condition     = var.replica_count >= 0 && var.replica_count <= 5
    error_message = "Replica count must be between 0 and 5."
  }
}

variable "replica_multi_az" {
  description = "Specifies if the read replicas should be deployed in multiple availability zones"
  type        = bool
  default     = true
}

variable "multi_az" {
  description = "Specifies if the primary RDS instance is multi-AZ for high availability"
  type        = bool
  default     = true
}

# Database Configuration
variable "engine_version" {
  description = "The PostgreSQL engine version to use - version 14 is required as per specifications"
  type        = string
  default     = "14"
  validation {
    condition     = var.engine_version == "14"
    error_message = "PostgreSQL version 14 is required as per the technical specification."
  }
}

variable "db_name" {
  description = "The name of the database to create when the DB instance is created"
  type        = string
  default     = "mcadb"
  validation {
    condition     = can(regex("^[a-zA-Z0-9_]+$", var.db_name))
    error_message = "Database name must contain only alphanumeric characters and underscores."
  }
}

variable "db_username" {
  description = "Username for the master DB user - should follow security best practices"
  type        = string
  default     = "postgres"
  sensitive   = true
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]+$", var.db_username))
    error_message = "Database username must start with a letter and contain only alphanumeric characters and underscores."
  }
}

variable "db_password" {
  description = "Password for the master DB user - must be strong and secure"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.db_password) >= 16
    error_message = "Database password must be at least 16 characters long for security."
  }
}

variable "db_port" {
  description = "The port on which the DB accepts connections"
  type        = number
  default     = 5432
  validation {
    condition     = var.db_port > 0 && var.db_port < 65536
    error_message = "Port must be between 1 and 65535."
  }
}

# Backup Configuration
variable "backup_retention_period" {
  description = "The days to retain backups for - 30 days as per requirements"
  type        = number
  default     = 30
  validation {
    condition     = var.backup_retention_period >= 7
    error_message = "Backup retention period must be at least 7 days for compliance."
  }
}

variable "backup_window" {
  description = "The daily time range during which automated backups are created (in UTC)"
  type        = string
  default     = "03:00-06:00"
  validation {
    condition     = can(regex("^[0-9]{2}:[0-9]{2}-[0-9]{2}:[0-9]{2}$", var.backup_window))
    error_message = "Backup window must be in the format HH:MM-HH:MM."
  }
}

variable "maintenance_window" {
  description = "The window to perform maintenance in (in UTC)"
  type        = string
  default     = "Sun:00:00-Sun:03:00"
  validation {
    condition     = can(regex("^[A-Za-z]{3}:[0-9]{2}:[0-9]{2}-[A-Za-z]{3}:[0-9]{2}:[0-9]{2}$", var.maintenance_window))
    error_message = "Maintenance window must be in the format Day:HH:MM-Day:HH:MM."
  }
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery with 5-minute RPO as specified in requirements"
  type        = bool
  default     = true
}

# Connection Pooling Configuration
variable "enable_connection_pooling" {
  description = "Enable PgBouncer connection pooling as specified in requirements"
  type        = bool
  default     = true
}

variable "connection_pooling_min" {
  description = "Minimum number of connections in the pool - 10 as per requirements"
  type        = number
  default     = 10
  validation {
    condition     = var.connection_pooling_min >= 5
    error_message = "Minimum connections must be at least 5."
  }
}

variable "connection_pooling_max" {
  description = "Maximum number of connections in the pool - 50 as per requirements"
  type        = number
  default     = 50
  validation {
    condition     = var.connection_pooling_max >= var.connection_pooling_min
    error_message = "Maximum connections must be greater than or equal to minimum connections."
  }
}

variable "connection_timeout" {
  description = "Connection timeout in seconds - 30 seconds as per requirements"
  type        = number
  default     = 30
  validation {
    condition     = var.connection_timeout >= 5 && var.connection_timeout <= 60
    error_message = "Connection timeout must be between 5 and 60 seconds."
  }
}

# Monitoring Configuration
variable "enable_enhanced_monitoring" {
  description = "Enable enhanced monitoring metrics with 15-second interval as per requirements"
  type        = bool
  default     = true
}

variable "monitoring_interval" {
  description = "The interval, in seconds, between points when Enhanced Monitoring metrics are collected - 15 seconds as per requirements"
  type        = number
  default     = 15
  validation {
    condition     = contains([0, 1, 5, 10, 15, 30, 60], var.monitoring_interval)
    error_message = "Monitoring interval must be one of: 0, 1, 5, 10, 15, 30, 60."
  }
}

variable "create_monitoring_role" {
  description = "Create an IAM role for enhanced monitoring"
  type        = bool
  default     = true
}

variable "enable_performance_insights" {
  description = "Enable performance insights for the database instance"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "The retention period for performance insights, in days"
  type        = number
  default     = 7
  validation {
    condition     = contains([7, 731], var.performance_insights_retention_period) || (var.performance_insights_retention_period >= 7 && var.performance_insights_retention_period <= 731)
    error_message = "Performance insights retention period must be between 7 and 731 days."
  }
}

# Security Configuration
variable "enable_encryption" {
  description = "Enable AES-256 encryption at rest for the RDS instance as per requirements"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "The ARN for the KMS encryption key if encryption is enabled - should be rotated every 90 days as per requirements"
  type        = string
  default     = null
}

variable "vpc_security_group_ids" {
  description = "List of VPC security groups to associate with the database instance"
  type        = list(string)
  default     = []
}

variable "subnet_ids" {
  description = "A list of VPC subnet IDs to place the DB instance and replicas - should be in different AZs for high availability"
  type        = list(string)
}

variable "enable_iam_database_authentication" {
  description = "Enable IAM database authentication"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection for the database instance"
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Specifies whether any database modifications are applied immediately, or during the next maintenance window"
  type        = bool
  default     = false
}

# Tags
variable "tags" {
  description = "A mapping of tags to assign to all resources for resource tracking and cost allocation"
  type        = map(string)
  default     = {}
}

# Auto-scaling configuration
variable "enable_autoscaling" {
  description = "Enable auto-scaling for the database instance"
  type        = bool
  default     = true
}

variable "autoscaling_max_capacity" {
  description = "Maximum capacity for autoscaling"
  type        = number
  default     = 8
}

variable "autoscaling_min_capacity" {
  description = "Minimum capacity for autoscaling"
  type        = number
  default     = 2
}

variable "autoscaling_target_cpu" {
  description = "Target CPU utilization (%) for autoscaling"
  type        = number
  default     = 70
  validation {
    condition     = var.autoscaling_target_cpu > 0 && var.autoscaling_target_cpu <= 100
    error_message = "Target CPU utilization must be between 1 and 100 percent."
  }
}

# High Availability Configuration
variable "high_availability" {
  description = "Enable high availability with 99.95% uptime guarantee as per requirements"
  type        = bool
  default     = true
}

variable "failover_target" {
  description = "Specifies whether the replica is the failover target"
  type        = bool
  default     = true
}