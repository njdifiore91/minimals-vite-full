# RabbitMQ Messaging Infrastructure Variables
# This file defines input variables for the RabbitMQ configuration, including environment-specific settings,
# cluster size, node types, security parameters, and monitoring integration.

# Environment Configuration
variable "environment" {
  description = "Deployment environment (production, staging, development)"
  type        = string
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development."
  }
}

# Region and Availability Zone Configuration
variable "region" {
  description = "AWS/Azure/GCP region for RabbitMQ deployment"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones for multi-AZ deployment"
  type        = list(string)
}

# Cluster Configuration
variable "cluster_name" {
  description = "Name of the RabbitMQ cluster"
  type        = string
  default     = "mca-rabbitmq"
}

variable "cluster_size" {
  description = "Number of nodes in the RabbitMQ cluster (minimum 3 for high availability)"
  type        = number
  default     = 3
  validation {
    condition     = var.cluster_size >= 3
    error_message = "Cluster size must be at least 3 nodes for high availability."
  }
}

# Node Configuration
variable "node_instance_type" {
  description = "Instance type for RabbitMQ nodes"
  type        = string
  default     = "m5.large"
}

variable "node_disk_size" {
  description = "Disk size in GB for RabbitMQ nodes"
  type        = number
  default     = 50
}

variable "node_disk_type" {
  description = "Disk type for RabbitMQ nodes (gp2, gp3, io1, etc.)"
  type        = string
  default     = "gp3"
}

# Message Persistence and Storage Settings
variable "message_persistence_enabled" {
  description = "Enable message persistence to disk"
  type        = bool
  default     = true
}

variable "message_ttl" {
  description = "Default message TTL in milliseconds (0 means no expiration)"
  type        = number
  default     = 0
}

variable "queue_mode" {
  description = "Queue mode (default or lazy). Lazy queues prioritize disk over memory for large messages."
  type        = string
  default     = "default"
  validation {
    condition     = contains(["default", "lazy"], var.queue_mode)
    error_message = "Queue mode must be either 'default' or 'lazy'."
  }
}

variable "disk_free_limit" {
  description = "Disk free space limit in bytes before RabbitMQ raises an alarm"
  type        = number
  default     = 50000000  # 50MB
}

# Security Configuration
variable "enable_tls" {
  description = "Enable TLS for RabbitMQ connections"
  type        = bool
  default     = true
}

variable "tls_version" {
  description = "TLS version for RabbitMQ connections"
  type        = string
  default     = "1.3"
  validation {
    condition     = contains(["1.2", "1.3"], var.tls_version)
    error_message = "TLS version must be either '1.2' or '1.3'."
  }
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate for TLS (AWS specific)"
  type        = string
  default     = ""
}

variable "enable_client_certificate_auth" {
  description = "Enable client certificate authentication"
  type        = bool
  default     = false
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to connect to RabbitMQ"
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
}

# Authentication Configuration
variable "admin_username" {
  description = "RabbitMQ admin username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "admin_password" {
  description = "RabbitMQ admin password"
  type        = string
  default     = null  # Should be provided via secure method, not hardcoded
  sensitive   = true
}

# Exchange and Queue Configuration
variable "exchanges" {
  description = "Map of exchanges to create"
  type = map(object({
    type        = string
    durable     = bool
    auto_delete = bool
  }))
  default = {
    "mca.documents" = {
      type        = "fanout"
      durable     = true
      auto_delete = false
    }
  }
}

variable "queues" {
  description = "Map of queues to create"
  type = map(object({
    durable     = bool
    auto_delete = bool
    arguments   = map(string)
  }))
  default = {
    "document-processing" = {
      durable     = true
      auto_delete = false
      arguments   = {}
    },
    "data-extraction" = {
      durable     = true
      auto_delete = false
      arguments   = {}
    },
    "notification" = {
      durable     = true
      auto_delete = false
      arguments   = {}
    }
  }
}

variable "bindings" {
  description = "Map of queue bindings to exchanges"
  type = map(object({
    exchange    = string
    queue       = string
    routing_key = string
  }))
  default = {
    "documents-processing" = {
      exchange    = "mca.documents"
      queue       = "document-processing"
      routing_key = "#"
    },
    "documents-extraction" = {
      exchange    = "mca.documents"
      queue       = "data-extraction"
      routing_key = "#"
    },
    "documents-notification" = {
      exchange    = "mca.documents"
      queue       = "notification"
      routing_key = "#"
    }
  }
}

# Monitoring Configuration
variable "enable_prometheus" {
  description = "Enable Prometheus metrics for RabbitMQ"
  type        = bool
  default     = true
}

variable "prometheus_endpoint" {
  description = "Endpoint for Prometheus metrics"
  type        = string
  default     = "/metrics"
}

variable "monitoring_namespace" {
  description = "Kubernetes namespace for monitoring resources"
  type        = string
  default     = "monitoring"
}

# Resource Limits
variable "memory_limit" {
  description = "Memory limit for RabbitMQ nodes in MB"
  type        = number
  default     = 2048
}

variable "cpu_limit" {
  description = "CPU limit for RabbitMQ nodes in millicores"
  type        = number
  default     = 1000
}

# High Availability Configuration
variable "ha_mode" {
  description = "High availability mode for queues (all, exactly, nodes)"
  type        = string
  default     = "all"
  validation {
    condition     = contains(["all", "exactly", "nodes"], var.ha_mode)
    error_message = "High availability mode must be one of: all, exactly, nodes."
  }
}

variable "ha_sync_mode" {
  description = "Synchronization mode for HA queues (automatic or manual)"
  type        = string
  default     = "automatic"
  validation {
    condition     = contains(["automatic", "manual"], var.ha_sync_mode)
    error_message = "Synchronization mode must be either 'automatic' or 'manual'."
  }
}

# Environment-specific defaults
variable "environment_defaults" {
  description = "Default values for different environments"
  type = map(object({
    cluster_size      = number
    node_instance_type = string
    node_disk_size    = number
    memory_limit      = number
    cpu_limit         = number
  }))
  default = {
    "production" = {
      cluster_size      = 5
      node_instance_type = "m5.xlarge"
      node_disk_size    = 100
      memory_limit      = 4096
      cpu_limit         = 2000
    },
    "staging" = {
      cluster_size      = 3
      node_instance_type = "m5.large"
      node_disk_size    = 50
      memory_limit      = 2048
      cpu_limit         = 1000
    },
    "development" = {
      cluster_size      = 3
      node_instance_type = "m5.large"
      node_disk_size    = 20
      memory_limit      = 1024
      cpu_limit         = 500
    }
  }
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}