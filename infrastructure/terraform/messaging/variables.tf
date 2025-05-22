# -----------------------------------------------------------------------------
# RabbitMQ Terraform Variables for MCA Application Processing System
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Environment Configuration
# -----------------------------------------------------------------------------

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "region" {
  description = "AWS region where RabbitMQ will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# Network Configuration
# -----------------------------------------------------------------------------

variable "vpc_id" {
  description = "ID of the VPC where RabbitMQ will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for RabbitMQ deployment (minimum 3 for multi-AZ)"
  type        = list(string)
  validation {
    condition     = length(var.private_subnet_ids) >= 3
    error_message = "At least 3 private subnet IDs are required for multi-AZ deployment."
  }
}

variable "service_security_group_ids" {
  description = "List of security group IDs that need access to RabbitMQ AMQP port"
  type        = list(string)
  default     = []
}

variable "management_security_group_ids" {
  description = "List of security group IDs that need access to RabbitMQ management UI"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# RabbitMQ Cluster Configuration
# -----------------------------------------------------------------------------

variable "broker_name" {
  description = "Name of the RabbitMQ broker"
  type        = string
  default     = "mca-rabbitmq-cluster"
}

variable "engine_version" {
  description = "RabbitMQ engine version"
  type        = string
  default     = "3.11.20"
}

variable "host_instance_type" {
  description = "Instance type for RabbitMQ nodes"
  type        = string
  default     = "mq.m5.large"
  validation {
    condition     = contains(["mq.t3.micro", "mq.m5.large", "mq.m5.xlarge", "mq.m5.2xlarge", "mq.m5.4xlarge"], var.host_instance_type)
    error_message = "Instance type must be one of the supported Amazon MQ for RabbitMQ instance types."
  }
}

variable "deployment_mode" {
  description = "Deployment mode for RabbitMQ (SINGLE_INSTANCE or CLUSTER_MULTI_AZ)"
  type        = string
  default     = "CLUSTER_MULTI_AZ"
  validation {
    condition     = contains(["SINGLE_INSTANCE", "CLUSTER_MULTI_AZ"], var.deployment_mode)
    error_message = "Deployment mode must be either SINGLE_INSTANCE or CLUSTER_MULTI_AZ."
  }
}

variable "auto_minor_version_upgrade" {
  description = "Enable automatic minor version upgrades"
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply changes immediately or during maintenance window"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# Maintenance Window Configuration
# -----------------------------------------------------------------------------

variable "maintenance_day_of_week" {
  description = "Day of week for maintenance window"
  type        = string
  default     = "Sunday"
  validation {
    condition     = contains(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], var.maintenance_day_of_week)
    error_message = "Day of week must be a valid day (Monday through Sunday)."
  }
}

variable "maintenance_time_of_day" {
  description = "Time of day for maintenance window (UTC)"
  type        = string
  default     = "02:00"
  validation {
    condition     = can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.maintenance_time_of_day))
    error_message = "Time of day must be in the format HH:MM (24-hour format)."
  }
}

variable "maintenance_time_zone" {
  description = "Time zone for maintenance window"
  type        = string
  default     = "UTC"
}

# -----------------------------------------------------------------------------
# Authentication Configuration
# -----------------------------------------------------------------------------

variable "rabbitmq_admin_username" {
  description = "Username for RabbitMQ admin user"
  type        = string
  sensitive   = true
}

variable "rabbitmq_admin_password" {
  description = "Password for RabbitMQ admin user"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.rabbitmq_admin_password) >= 12
    error_message = "Password must be at least 12 characters long."
  }
}

# -----------------------------------------------------------------------------
# Security Configuration
# -----------------------------------------------------------------------------

variable "enable_tls" {
  description = "Enable TLS for RabbitMQ connections"
  type        = bool
  default     = true
}

variable "tls_version" {
  description = "TLS version for RabbitMQ connections"
  type        = string
  default     = "TLS1.3"
  validation {
    condition     = contains(["TLS1.2", "TLS1.3"], var.tls_version)
    error_message = "TLS version must be either TLS1.2 or TLS1.3."
  }
}

variable "publicly_accessible" {
  description = "Make broker publicly accessible (not recommended for production)"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------

variable "enable_general_logs" {
  description = "Enable general logs for RabbitMQ"
  type        = bool
  default     = true
}

variable "enable_audit_logs" {
  description = "Enable audit logs for RabbitMQ"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Queue Configuration
# -----------------------------------------------------------------------------

variable "queue_message_ttl" {
  description = "Message TTL for queues in milliseconds (7 days default)"
  type        = number
  default     = 604800000 # 7 days in milliseconds
}

variable "enable_lazy_queues" {
  description = "Enable lazy queues for optimizing memory usage with large messages"
  type        = bool
  default     = true
}

variable "queue_ha_mode" {
  description = "High availability mode for queues (all, exactly, nodes)"
  type        = string
  default     = "all"
  validation {
    condition     = contains(["all", "exactly", "nodes"], var.queue_ha_mode)
    error_message = "HA mode must be one of: all, exactly, nodes."
  }
}

variable "queue_ha_sync_mode" {
  description = "Synchronization mode for HA queues (automatic or manual)"
  type        = string
  default     = "automatic"
  validation {
    condition     = contains(["automatic", "manual"], var.queue_ha_sync_mode)
    error_message = "HA sync mode must be either automatic or manual."
  }
}

variable "queue_ha_sync_batch_size" {
  description = "Batch size for synchronizing HA queues"
  type        = number
  default     = 1000
}

# -----------------------------------------------------------------------------
# Exchange Configuration
# -----------------------------------------------------------------------------

variable "exchange_name" {
  description = "Name of the main exchange for document processing"
  type        = string
  default     = "mca.documents"
}

variable "exchange_type" {
  description = "Type of the main exchange (fanout, direct, topic, headers)"
  type        = string
  default     = "fanout"
  validation {
    condition     = contains(["fanout", "direct", "topic", "headers"], var.exchange_type)
    error_message = "Exchange type must be one of: fanout, direct, topic, headers."
  }
}

# -----------------------------------------------------------------------------
# Queue Names Configuration
# -----------------------------------------------------------------------------

variable "document_processing_queue_name" {
  description = "Name of the document processing queue"
  type        = string
  default     = "document-processing"
}

variable "data_extraction_queue_name" {
  description = "Name of the data extraction queue"
  type        = string
  default     = "data-extraction"
}

variable "notification_queue_name" {
  description = "Name of the notification queue"
  type        = string
  default     = "notification"
}

# -----------------------------------------------------------------------------
# Monitoring Configuration
# -----------------------------------------------------------------------------

variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms for RabbitMQ monitoring"
  type        = bool
  default     = true
}

variable "cpu_utilization_threshold" {
  description = "CPU utilization threshold for CloudWatch alarm (percentage)"
  type        = number
  default     = 80
  validation {
    condition     = var.cpu_utilization_threshold > 0 && var.cpu_utilization_threshold <= 100
    error_message = "CPU utilization threshold must be between 1 and 100."
  }
}

variable "memory_usage_threshold" {
  description = "Memory usage threshold for CloudWatch alarm (percentage)"
  type        = number
  default     = 80
  validation {
    condition     = var.memory_usage_threshold > 0 && var.memory_usage_threshold <= 100
    error_message = "Memory usage threshold must be between 1 and 100."
  }
}

variable "queue_depth_threshold" {
  description = "Queue depth threshold for CloudWatch alarm"
  type        = number
  default     = 10000
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for CloudWatch alarms"
  type        = string
}

variable "enable_prometheus_monitoring" {
  description = "Enable Prometheus monitoring for RabbitMQ"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Environment-Specific Defaults
# -----------------------------------------------------------------------------

variable "environment_defaults" {
  description = "Default values for different environments"
  type        = map(any)
  default     = {
    development = {
      host_instance_type = "mq.t3.micro"
      deployment_mode    = "SINGLE_INSTANCE"
      enable_audit_logs  = false
    },
    staging = {
      host_instance_type = "mq.m5.large"
      deployment_mode    = "CLUSTER_MULTI_AZ"
      enable_audit_logs  = true
    },
    production = {
      host_instance_type = "mq.m5.xlarge"
      deployment_mode    = "CLUSTER_MULTI_AZ"
      enable_audit_logs  = true
    }
  }
}