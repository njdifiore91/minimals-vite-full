# =========================================
# Development Environment Variables
# =========================================
# This file defines all input variables for the development environment Terraform configuration,
# including region, resource sizes, and feature flags. It enables parameterized deployment of
# the development infrastructure and serves as the configuration interface for the environment.

# =========================================
# Cloud Provider and Region Variables
# =========================================

variable "cloud_provider" {
  description = "The cloud provider to use (aws, azure, gcp)"
  type        = string
  default     = "aws"
  validation {
    condition     = contains(["aws", "azure", "gcp"], var.cloud_provider)
    error_message = "Valid values for cloud_provider are: aws, azure, gcp"
  }
}

variable "region" {
  description = "The region to deploy resources to"
  type        = string
  default     = "us-east-1"  # Default region for development
}

variable "availability_zones" {
  description = "List of availability zones to use within the region"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]  # Using 2 AZs for development
}

# =========================================
# Resource Sizing Variables (Development)
# =========================================

variable "database_instance_class" {
  description = "The instance class for the PostgreSQL database"
  type        = string
  default     = "db.t3.medium"  # Smaller instance for development
}

variable "redis_node_type" {
  description = "The node type for Redis cache instances"
  type        = string
  default     = "cache.t3.small"  # Smaller instance for development
}

variable "rabbitmq_instance_type" {
  description = "The instance type for RabbitMQ nodes"
  type        = string
  default     = "t3.small"  # Smaller instance for development
}

variable "kubernetes_node_type" {
  description = "The instance type for Kubernetes worker nodes"
  type        = string
  default     = "t3.medium"  # Smaller instance for development
}

variable "kubernetes_node_count" {
  description = "The number of Kubernetes worker nodes"
  type        = number
  default     = 2  # Fewer nodes for development
}

variable "gpu_node_type" {
  description = "The instance type for GPU-enabled Kubernetes nodes for OCR service"
  type        = string
  default     = "g4dn.xlarge"  # GPU instance for OCR processing
}

variable "gpu_node_count" {
  description = "The number of GPU-enabled Kubernetes nodes"
  type        = number
  default     = 1  # Minimum for development
}

# =========================================
# Feature Flag Variables
# =========================================

variable "enable_gpu_nodes" {
  description = "Whether to enable GPU nodes for OCR processing"
  type        = bool
  default     = true  # Enable GPU nodes by default for OCR service
}

variable "enable_monitoring" {
  description = "Whether to enable comprehensive monitoring"
  type        = bool
  default     = true
}

variable "enable_auto_scaling" {
  description = "Whether to enable auto-scaling for Kubernetes nodes"
  type        = bool
  default     = false  # Disabled for development to save costs
}

variable "enable_multi_region" {
  description = "Whether to enable multi-region deployment"
  type        = bool
  default     = false  # Single region for development
}

variable "enable_disaster_recovery" {
  description = "Whether to enable disaster recovery features"
  type        = bool
  default     = false  # Disabled for development to save costs
}

# =========================================
# Database Configuration Variables
# =========================================

variable "postgres_version" {
  description = "The version of PostgreSQL to use"
  type        = string
  default     = "14"  # As specified in the technical requirements
}

variable "postgres_db_name" {
  description = "The name of the PostgreSQL database"
  type        = string
  default     = "mca_development"
}

variable "postgres_port" {
  description = "The port for PostgreSQL"
  type        = number
  default     = 5432
}

variable "postgres_min_connections" {
  description = "Minimum number of database connections in the pool"
  type        = number
  default     = 10  # As specified in the technical requirements
}

variable "postgres_max_connections" {
  description = "Maximum number of database connections in the pool"
  type        = number
  default     = 50  # As specified in the technical requirements
}

variable "postgres_read_replica_count" {
  description = "Number of PostgreSQL read replicas"
  type        = number
  default     = 1  # 1 read replica for development (2+ for production)
}

variable "postgres_backup_retention_days" {
  description = "Number of days to retain PostgreSQL backups"
  type        = number
  default     = 7  # Shorter retention for development
}

# =========================================
# Messaging Configuration Variables
# =========================================

variable "rabbitmq_version" {
  description = "The version of RabbitMQ to use"
  type        = string
  default     = "3.11"
}

variable "rabbitmq_cluster_size" {
  description = "Number of nodes in the RabbitMQ cluster"
  type        = number
  default     = 3  # Minimum 3-node cluster as specified
}

variable "rabbitmq_vhost" {
  description = "The RabbitMQ virtual host to use"
  type        = string
  default     = "mca_development"
}

variable "rabbitmq_exchanges" {
  description = "Map of RabbitMQ exchanges to create"
  type        = map(object({
    type        = string
    durable     = bool
    auto_delete = bool
  }))
  default     = {
    "mca.documents" = {
      type        = "fanout"
      durable     = true
      auto_delete = false
    }
  }
}

variable "rabbitmq_queues" {
  description = "List of RabbitMQ queues to create"
  type        = list(string)
  default     = ["document-processing", "data-extraction", "notification"]
}

# =========================================
# Cache Configuration Variables
# =========================================

variable "redis_version" {
  description = "The version of Redis to use"
  type        = string
  default     = "7.0"  # As specified in the technical requirements
}

variable "redis_cluster_enabled" {
  description = "Whether to enable Redis cluster mode"
  type        = bool
  default     = true
}

variable "redis_shard_count" {
  description = "Number of shards in the Redis cluster"
  type        = number
  default     = 3  # Minimum 3 shards as specified
}

variable "redis_replica_per_shard" {
  description = "Number of replicas per shard in the Redis cluster"
  type        = number
  default     = 1  # Minimum 1 replica per shard as specified
}

variable "redis_data_ttl_minutes" {
  description = "TTL for application data in Redis (minutes)"
  type        = number
  default     = 15  # 15 minutes TTL for application data as specified
}

variable "redis_session_ttl_hours" {
  description = "TTL for user sessions in Redis (hours)"
  type        = number
  default     = 24  # 24 hours TTL for user sessions as specified
}

variable "redis_eviction_policy_cache" {
  description = "Eviction policy for Redis cache instances"
  type        = string
  default     = "allkeys-lru"  # As specified in the technical requirements
}

variable "redis_eviction_policy_session" {
  description = "Eviction policy for Redis session instances"
  type        = string
  default     = "noeviction"  # As specified in the technical requirements
}

# =========================================
# Storage Configuration Variables
# =========================================

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for document storage"
  type        = string
  default     = "mca-documents-development"
}

variable "s3_versioning_enabled" {
  description = "Whether to enable versioning for the S3 bucket"
  type        = bool
  default     = true
}

variable "s3_encryption_algorithm" {
  description = "Encryption algorithm for S3 objects"
  type        = string
  default     = "AES256"  # AES-256 encryption as specified
}

variable "s3_signed_url_expiry" {
  description = "Expiration time for signed URLs in seconds"
  type        = number
  default     = 900  # 15 minutes (900 seconds) as specified
}

# =========================================
# Local Development Settings
# =========================================

variable "local_development_mode" {
  description = "Whether to enable local development mode"
  type        = bool
  default     = true
}

variable "debug_enabled" {
  description = "Whether to enable debug mode"
  type        = bool
  default     = true  # Enable debug for development
}

variable "log_level" {
  description = "The log level to use"
  type        = string
  default     = "DEBUG"  # More verbose logging for development
  validation {
    condition     = contains(["ERROR", "WARN", "INFO", "DEBUG"], var.log_level)
    error_message = "Valid values for log_level are: ERROR, WARN, INFO, DEBUG"
  }
}

# =========================================
# Kubernetes Configuration Variables
# =========================================

variable "kubernetes_version" {
  description = "The version of Kubernetes to use"
  type        = string
  default     = "1.27"
}

variable "kubernetes_namespace" {
  description = "The Kubernetes namespace to use"
  type        = string
  default     = "mca-development"
}

variable "kubernetes_service_account" {
  description = "The Kubernetes service account to use"
  type        = string
  default     = "mca-service-account"
}

# =========================================
# API Gateway Configuration Variables
# =========================================

variable "api_gateway_type" {
  description = "The type of API Gateway to use (kong)"
  type        = string
  default     = "kong"
}

variable "api_rate_limit" {
  description = "Rate limit for API requests (requests per minute)"
  type        = number
  default     = 300  # Higher limit for development
}

variable "jwt_token_expiry_minutes" {
  description = "Expiry time for JWT tokens in minutes"
  type        = number
  default     = 60  # 60 minutes as specified
}

variable "jwt_refresh_token_expiry_days" {
  description = "Expiry time for JWT refresh tokens in days"
  type        = number
  default     = 7  # 7 days as specified
}

# =========================================
# Monitoring Configuration Variables
# =========================================

variable "monitoring_provider" {
  description = "The monitoring provider to use (datadog, prometheus)"
  type        = string
  default     = "prometheus"  # Self-hosted option for development
  validation {
    condition     = contains(["datadog", "prometheus"], var.monitoring_provider)
    error_message = "Valid values for monitoring_provider are: datadog, prometheus"
  }
}

variable "metrics_retention_days" {
  description = "Number of days to retain metrics"
  type        = number
  default     = 30  # 30 days for development
}

variable "enable_log_aggregation" {
  description = "Whether to enable log aggregation"
  type        = bool
  default     = true
}

variable "enable_tracing" {
  description = "Whether to enable distributed tracing"
  type        = bool
  default     = true
}

# =========================================
# Email Service Configuration Variables
# =========================================

variable "email_imap_server" {
  description = "IMAP server for email monitoring"
  type        = string
  default     = "imap.example.com"  # Placeholder for development
}

variable "email_imap_port" {
  description = "IMAP port for email monitoring"
  type        = number
  default     = 993
}

variable "email_polling_interval_seconds" {
  description = "Interval for polling emails in seconds"
  type        = number
  default     = 60  # More frequent polling for development
}

# =========================================
# Tags
# =========================================

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {
    Environment = "development"
    Project     = "MCA"
    ManagedBy   = "Terraform"
  }
}