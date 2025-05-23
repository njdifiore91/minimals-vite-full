# -----------------------------------------------
# PostgreSQL Database Configuration Variables
# -----------------------------------------------

# Environment Configuration
# -----------------------------------------------

variable "environment" {
  description = "Deployment environment (production, staging, development)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development."
  }
}

# Instance Configuration
# -----------------------------------------------

variable "primary_instance_type" {
  description = "Instance type for the primary PostgreSQL database"
  type        = map(string)
  default = {
    production  = "db.m5.xlarge"  # 4 vCPU, 16 GiB RAM
    staging     = "db.m5.large"   # 2 vCPU, 8 GiB RAM
    development = "db.m5.large"   # 2 vCPU, 8 GiB RAM
  }
}

variable "replica_instance_type" {
  description = "Instance type for PostgreSQL read replicas"
  type        = map(string)
  default = {
    production  = "db.m5.large"    # 2 vCPU, 8 GiB RAM
    staging     = "db.m5.large"    # 2 vCPU, 8 GiB RAM
    development = "db.t3.medium"   # 2 vCPU, 4 GiB RAM
  }
}

variable "replica_count" {
  description = "Number of read replicas to deploy"
  type        = map(number)
  default = {
    production  = 2
    staging     = 1
    development = 0
  }
}

# Storage Configuration
# -----------------------------------------------

variable "allocated_storage" {
  description = "Allocated storage size in GB for the primary database"
  type        = map(number)
  default = {
    production  = 100
    staging     = 50
    development = 20
  }
}

variable "max_allocated_storage" {
  description = "Maximum storage size in GB for autoscaling"
  type        = map(number)
  default = {
    production  = 500
    staging     = 200
    development = 100
  }
}

variable "storage_type" {
  description = "Storage type for the database (gp2, gp3, io1)"
  type        = string
  default     = "gp3"
}

variable "iops" {
  description = "Provisioned IOPS for the database storage"
  type        = map(number)
  default = {
    production  = 3000
    staging     = 1000
    development = 1000
  }
}

# Backup Configuration
# -----------------------------------------------

variable "backup_retention_period" {
  description = "Number of days to retain automated backups"
  type        = map(number)
  default = {
    production  = 30
    staging     = 14
    development = 7
  }
}

variable "backup_window" {
  description = "Daily time range during which backups are created (UTC)"
  type        = string
  default     = "03:00-05:00"
}

variable "maintenance_window" {
  description = "Weekly time range during which maintenance can occur (UTC)"
  type        = string
  default     = "sun:05:00-sun:07:00"
}

variable "snapshot_identifier" {
  description = "Specifies whether to create the database from a snapshot"
  type        = string
  default     = null
}

# Security Configuration
# -----------------------------------------------

variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "mca_application"
}

variable "db_username" {
  description = "Username for the master DB user"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_password" {
  description = "Password for the master DB user"
  type        = string
  sensitive   = true
}

variable "db_port" {
  description = "Port on which the PostgreSQL instance accepts connections"
  type        = number
  default     = 5432
}

variable "publicly_accessible" {
  description = "Specifies whether the database should be publicly accessible"
  type        = map(bool)
  default = {
    production  = false
    staging     = false
    development = true
  }
}

variable "vpc_security_group_ids" {
  description = "List of VPC security group IDs to associate with the database"
  type        = list(string)
  default     = []
}

variable "subnet_ids" {
  description = "List of subnet IDs to use for the database subnet group"
  type        = list(string)
  default     = []
}

variable "storage_encrypted" {
  description = "Specifies whether the database storage should be encrypted"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "ARN of the KMS key for storage encryption"
  type        = string
  default     = null
}

# Connection Pooling Configuration
# -----------------------------------------------

variable "enable_connection_pooling" {
  description = "Specifies whether to enable connection pooling with PgBouncer"
  type        = bool
  default     = true
}

variable "connection_pool_min_size" {
  description = "Minimum number of connections in the pool"
  type        = number
  default     = 10
}

variable "connection_pool_max_size" {
  description = "Maximum number of connections in the pool"
  type        = number
  default     = 50
}

variable "connection_pool_timeout" {
  description = "Connection timeout in seconds"
  type        = number
  default     = 30
}

# High Availability Configuration
# -----------------------------------------------

variable "multi_az" {
  description = "Specifies whether the database should be deployed in multiple availability zones"
  type        = map(bool)
  default = {
    production  = true
    staging     = true
    development = false
  }
}

variable "availability_zone" {
  description = "Availability zone for the primary database (if multi_az is false)"
  type        = string
  default     = null
}

variable "replica_availability_zones" {
  description = "List of availability zones for read replicas"
  type        = list(string)
  default     = []
}

# Performance and Monitoring Configuration
# -----------------------------------------------

variable "enable_enhanced_monitoring" {
  description = "Specifies whether to enable enhanced monitoring"
  type        = map(bool)
  default = {
    production  = true
    staging     = true
    development = false
  }
}

variable "monitoring_interval" {
  description = "Interval in seconds for enhanced monitoring metrics collection"
  type        = number
  default     = 15
}

variable "monitoring_role_arn" {
  description = "ARN of the IAM role for enhanced monitoring"
  type        = string
  default     = null
}

variable "performance_insights_enabled" {
  description = "Specifies whether to enable Performance Insights"
  type        = map(bool)
  default = {
    production  = true
    staging     = true
    development = false
  }
}

variable "performance_insights_retention_period" {
  description = "Retention period in days for Performance Insights data"
  type        = number
  default     = 7
}

# Additional Configuration
# -----------------------------------------------

variable "parameter_group_name" {
  description = "Name of the DB parameter group to associate with the database"
  type        = string
  default     = null
}

variable "option_group_name" {
  description = "Name of the DB option group to associate with the database"
  type        = string
  default     = null
}

variable "apply_immediately" {
  description = "Specifies whether any database modifications are applied immediately"
  type        = bool
  default     = false
}

variable "auto_minor_version_upgrade" {
  description = "Specifies whether minor engine upgrades are applied automatically"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Specifies whether the database can be deleted"
  type        = map(bool)
  default = {
    production  = true
    staging     = true
    development = false
  }
}

variable "skip_final_snapshot" {
  description = "Determines whether a final DB snapshot is created before deletion"
  type        = map(bool)
  default = {
    production  = false
    staging     = false
    development = true
  }
}

variable "final_snapshot_identifier_prefix" {
  description = "Prefix for the name of the final DB snapshot"
  type        = string
  default     = "final-snapshot"
}

variable "tags" {
  description = "Map of tags to apply to the database resources"
  type        = map(string)
  default     = {}
}