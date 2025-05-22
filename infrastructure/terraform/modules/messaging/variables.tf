# RabbitMQ Messaging Module Variables

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "region" {
  description = "AWS region or cloud provider region to deploy RabbitMQ"
  type        = string
  default     = "us-east-1"
}

variable "availability_zones" {
  description = "List of availability zones for multi-AZ deployment"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# Cluster configuration
variable "cluster_name" {
  description = "Name of the RabbitMQ cluster"
  type        = string
  default     = "mca-rabbitmq"
}

variable "cluster_size" {
  description = "Number of nodes in the RabbitMQ cluster"
  type        = number
  default     = 3
  validation {
    condition     = var.cluster_size >= 3
    error_message = "Cluster size must be at least 3 nodes for high availability."
  }
}

variable "instance_type" {
  description = "Instance type for RabbitMQ nodes"
  type        = string
  default     = "m5.large"
}

# Storage configuration
variable "storage_type" {
  description = "Type of storage for message persistence (gp2, gp3, io1)"
  type        = string
  default     = "gp3"
  validation {
    condition     = contains(["gp2", "gp3", "io1"], var.storage_type)
    error_message = "Storage type must be one of: gp2, gp3, io1."
  }
}

variable "storage_size" {
  description = "Size of storage volume in GB"
  type        = number
  default     = 100
}

variable "storage_iops" {
  description = "Provisioned IOPS for storage (only applicable for io1 or gp3)"
  type        = number
  default     = 3000
}

# RabbitMQ configuration
variable "rabbitmq_version" {
  description = "Version of RabbitMQ to deploy"
  type        = string
  default     = "3.11"
}

variable "admin_username" {
  description = "Username for RabbitMQ administrator"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "admin_password" {
  description = "Password for RabbitMQ administrator"
  type        = string
  sensitive   = true
}

variable "enable_tls" {
  description = "Enable TLS for RabbitMQ connections"
  type        = bool
  default     = true
}

variable "tls_certificate_arn" {
  description = "ARN of the TLS certificate in ACM or similar service"
  type        = string
  default     = ""
}

# Queue and exchange configuration
variable "create_default_resources" {
  description = "Create default exchanges and queues for MCA application"
  type        = bool
  default     = true
}

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
      arguments   = { "x-queue-mode" = "lazy" }
    },
    "data-extraction" = {
      durable     = true
      auto_delete = false
      arguments   = { "x-queue-mode" = "lazy" }
    },
    "notification" = {
      durable     = true
      auto_delete = false
      arguments   = { "x-queue-mode" = "lazy" }
    }
  }
}

variable "bindings" {
  description = "Map of bindings between exchanges and queues"
  type = map(object({
    exchange    = string
    queue       = string
    routing_key = string
  }))
  default = {
    "documents-to-processing" = {
      exchange    = "mca.documents"
      queue       = "document-processing"
      routing_key = "#"
    },
    "documents-to-extraction" = {
      exchange    = "mca.documents"
      queue       = "data-extraction"
      routing_key = "#"
    },
    "documents-to-notification" = {
      exchange    = "mca.documents"
      queue       = "notification"
      routing_key = "#"
    }
  }
}

# Monitoring and alerting
variable "enable_monitoring" {
  description = "Enable Prometheus monitoring for RabbitMQ"
  type        = bool
  default     = true
}

variable "enable_dashboard" {
  description = "Enable RabbitMQ management dashboard"
  type        = bool
  default     = true
}

variable "dashboard_port" {
  description = "Port for RabbitMQ management dashboard"
  type        = number
  default     = 15672
}

# High availability settings
variable "enable_mirrored_queues" {
  description = "Enable mirrored queues for high availability"
  type        = bool
  default     = true
}

variable "mirror_sync_batch_size" {
  description = "Batch size for synchronizing mirrored queues"
  type        = number
  default     = 4096
}

# Resource allocation
variable "memory_high_watermark" {
  description = "Memory high watermark for RabbitMQ (0.0-1.0)"
  type        = number
  default     = 0.7
  validation {
    condition     = var.memory_high_watermark > 0 && var.memory_high_watermark <= 1.0
    error_message = "Memory high watermark must be between 0.0 and 1.0."
  }
}

variable "cpu_high_watermark" {
  description = "CPU high watermark for RabbitMQ (0.0-1.0)"
  type        = number
  default     = 0.8
  validation {
    condition     = var.cpu_high_watermark > 0 && var.cpu_high_watermark <= 1.0
    error_message = "CPU high watermark must be between 0.0 and 1.0."
  }
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}