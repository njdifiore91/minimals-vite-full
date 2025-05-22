# =========================================
# Environment Variables
# =========================================

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "region" {
  description = "Primary AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "availability_zones" {
  description = "List of availability zones to use for resources"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "enable_disaster_recovery" {
  description = "Enable cross-region disaster recovery capabilities"
  type        = bool
  default     = false
}

variable "dr_region" {
  description = "Secondary region for disaster recovery (if enabled)"
  type        = string
  default     = "us-west-2"
}

# =========================================
# Database Variables (PostgreSQL)
# =========================================

variable "postgres_instance_type" {
  description = "PostgreSQL instance type based on environment"
  type        = map(string)
  default     = {
    development = "db.t3.medium"
    staging     = "db.m5.large"
    production  = "db.m5.xlarge"
  }
}

variable "postgres_replica_count" {
  description = "Number of PostgreSQL read replicas per environment"
  type        = map(number)
  default     = {
    development = 0
    staging     = 1
    production  = 2
  }
}

variable "postgres_storage_gb" {
  description = "Allocated storage in GB for PostgreSQL instances"
  type        = map(number)
  default     = {
    development = 20
    staging     = 50
    production  = 100
  }
}

variable "postgres_backup_retention_days" {
  description = "Number of days to retain automated PostgreSQL backups"
  type        = number
  default     = 30
}

variable "postgres_multi_az" {
  description = "Enable Multi-AZ deployment for PostgreSQL primary instance"
  type        = map(bool)
  default     = {
    development = false
    staging     = true
    production  = true
  }
}

variable "postgres_connection_pool_min" {
  description = "Minimum number of database connections in the pool"
  type        = number
  default     = 10
}

variable "postgres_connection_pool_max" {
  description = "Maximum number of database connections in the pool"
  type        = number
  default     = 50
}

variable "postgres_connection_timeout" {
  description = "Connection timeout in seconds for PostgreSQL connections"
  type        = number
  default     = 30
}

# =========================================
# Messaging Variables (RabbitMQ)
# =========================================

variable "rabbitmq_instance_type" {
  description = "RabbitMQ instance type based on environment"
  type        = map(string)
  default     = {
    development = "t3.small"
    staging     = "m5.large"
    production  = "m5.xlarge"
  }
}

variable "rabbitmq_cluster_size" {
  description = "Number of nodes in RabbitMQ cluster per environment"
  type        = map(number)
  default     = {
    development = 1
    staging     = 3
    production  = 3
  }
}

variable "rabbitmq_enable_mirroring" {
  description = "Enable queue mirroring for high availability"
  type        = bool
  default     = true
}

variable "rabbitmq_exchanges" {
  description = "List of RabbitMQ exchanges to create"
  type        = list(object({
    name       = string
    type       = string
    durable    = bool
    auto_delete = bool
  }))
  default     = [
    {
      name       = "mca.documents"
      type       = "fanout"
      durable    = true
      auto_delete = false
    }
  ]
}

variable "rabbitmq_queues" {
  description = "List of RabbitMQ queues to create"
  type        = list(object({
    name       = string
    durable    = bool
    auto_delete = bool
  }))
  default     = [
    {
      name       = "document-processing"
      durable    = true
      auto_delete = false
    },
    {
      name       = "data-extraction"
      durable    = true
      auto_delete = false
    },
    {
      name       = "notification"
      durable    = true
      auto_delete = false
    }
  ]
}

# =========================================
# Cache Variables (Redis)
# =========================================

variable "redis_instance_type" {
  description = "Redis instance type based on environment"
  type        = map(string)
  default     = {
    development = "cache.t3.small"
    staging     = "cache.m5.large"
    production  = "cache.m5.xlarge"
  }
}

variable "redis_cluster_size" {
  description = "Number of shards in Redis cluster per environment"
  type        = map(number)
  default     = {
    development = 1
    staging     = 2
    production  = 3
  }
}

variable "redis_replicas_per_shard" {
  description = "Number of replicas per Redis shard"
  type        = map(number)
  default     = {
    development = 0
    staging     = 1
    production  = 1
  }
}

variable "redis_data_tiering_enabled" {
  description = "Enable data tiering for Redis (SSD for less frequently accessed data)"
  type        = bool
  default     = true
}

variable "redis_cache_ttl" {
  description = "TTL for application data cache in seconds (15 minutes)"
  type        = number
  default     = 900
}

variable "redis_session_ttl" {
  description = "TTL for user sessions in seconds (24 hours)"
  type        = number
  default     = 86400
}

variable "redis_eviction_policy" {
  description = "Redis eviction policy for cache instances"
  type        = string
  default     = "allkeys-lru"
  validation {
    condition     = contains(["noeviction", "allkeys-lru", "volatile-lru", "allkeys-random", "volatile-random", "volatile-ttl"], var.redis_eviction_policy)
    error_message = "Eviction policy must be one of: noeviction, allkeys-lru, volatile-lru, allkeys-random, volatile-random, volatile-ttl."
  }
}

variable "redis_session_eviction_policy" {
  description = "Redis eviction policy for session instances"
  type        = string
  default     = "noeviction"
  validation {
    condition     = contains(["noeviction", "allkeys-lru", "volatile-lru", "allkeys-random", "volatile-random", "volatile-ttl"], var.redis_session_eviction_policy)
    error_message = "Eviction policy must be one of: noeviction, allkeys-lru, volatile-lru, allkeys-random, volatile-random, volatile-ttl."
  }
}

# =========================================
# Storage Variables (S3)
# =========================================

variable "s3_bucket_name_prefix" {
  description = "Prefix for S3 bucket names"
  type        = string
  default     = "mca-documents"
}

variable "s3_bucket_names" {
  description = "Map of environment-specific S3 bucket names"
  type        = map(string)
  default     = {
    development = "mca-documents-development"
    staging     = "mca-documents-staging"
    production  = "mca-documents-production"
  }
}

variable "s3_enable_versioning" {
  description = "Enable versioning for S3 buckets"
  type        = bool
  default     = true
}

variable "s3_enable_encryption" {
  description = "Enable server-side encryption for S3 buckets"
  type        = bool
  default     = true
}

variable "s3_encryption_algorithm" {
  description = "Server-side encryption algorithm for S3 buckets"
  type        = string
  default     = "AES256"
}

variable "s3_lifecycle_rules" {
  description = "Lifecycle rules for S3 buckets"
  type        = list(object({
    id                       = string
    status                   = string
    transition_days          = number
    transition_storage_class = string
    expiration_days          = number
  }))
  default     = [
    {
      id                       = "archive-rule"
      status                   = "Enabled"
      transition_days          = 90
      transition_storage_class = "STANDARD_IA"
      expiration_days          = 0  # No expiration
    }
  ]
}

variable "s3_signed_url_expiry" {
  description = "Expiration time in seconds for signed URLs (15 minutes)"
  type        = number
  default     = 900
}

# =========================================
# Kubernetes Variables
# =========================================

variable "kubernetes_version" {
  description = "Kubernetes version to use for the cluster"
  type        = string
  default     = "1.27"
}

variable "kubernetes_node_groups" {
  description = "Configuration for Kubernetes node groups"
  type        = map(object({
    instance_type  = string
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
  }))
  default     = {
    general = {
      instance_type  = "m5.large"
      min_size       = 2
      max_size       = 5
      desired_size   = 2
      disk_size      = 50
    },
    gpu = {
      instance_type  = "g4dn.xlarge"
      min_size       = 1
      max_size       = 3
      desired_size   = 1
      disk_size      = 100
    }
  }
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace for MCA application"
  type        = string
  default     = "mca"
}

# =========================================
# Microservices Variables
# =========================================

variable "email_service_config" {
  description = "Configuration for Email Service"
  type        = object({
    replicas         = number
    cpu_request      = string
    memory_request   = string
    cpu_limit        = string
    memory_limit     = string
    imap_poll_interval = number
  })
  default     = {
    replicas         = 2
    cpu_request      = "100m"
    memory_request   = "256Mi"
    cpu_limit        = "500m"
    memory_limit     = "512Mi"
    imap_poll_interval = 60
  }
}

variable "document_service_config" {
  description = "Configuration for Document Service"
  type        = object({
    replicas         = number
    cpu_request      = string
    memory_request   = string
    cpu_limit        = string
    memory_limit     = string
  })
  default     = {
    replicas         = 2
    cpu_request      = "500m"
    memory_request   = "1Gi"
    cpu_limit        = "1000m"
    memory_limit     = "2Gi"
  }
}

variable "ocr_service_config" {
  description = "Configuration for OCR Service"
  type        = object({
    replicas         = number
    cpu_request      = string
    memory_request   = string
    cpu_limit        = string
    memory_limit     = string
    gpu_enabled      = bool
    gpu_limit        = string
  })
  default     = {
    replicas         = 2
    cpu_request      = "500m"
    memory_request   = "2Gi"
    cpu_limit        = "2000m"
    memory_limit     = "4Gi"
    gpu_enabled      = true
    gpu_limit        = "1"
  }
}

variable "data_service_config" {
  description = "Configuration for Data Service"
  type        = object({
    replicas         = number
    cpu_request      = string
    memory_request   = string
    cpu_limit        = string
    memory_limit     = string
    java_opts        = string
  })
  default     = {
    replicas         = 2
    cpu_request      = "500m"
    memory_request   = "1Gi"
    cpu_limit        = "1000m"
    memory_limit     = "2Gi"
    java_opts        = "-Xms512m -Xmx1536m"
  }
}

variable "notification_service_config" {
  description = "Configuration for Notification Service"
  type        = object({
    replicas         = number
    cpu_request      = string
    memory_request   = string
    cpu_limit        = string
    memory_limit     = string
    webhook_retry_attempts = number
    webhook_retry_delay_seconds = number
  })
  default     = {
    replicas         = 2
    cpu_request      = "100m"
    memory_request   = "256Mi"
    cpu_limit        = "500m"
    memory_limit     = "512Mi"
    webhook_retry_attempts = 3
    webhook_retry_delay_seconds = 60
  }
}

variable "api_gateway_config" {
  description = "Configuration for API Gateway"
  type        = object({
    replicas         = number
    cpu_request      = string
    memory_request   = string
    cpu_limit        = string
    memory_limit     = string
    rate_limiting_enabled = bool
    rate_limit_per_minute = number
  })
  default     = {
    replicas         = 2
    cpu_request      = "200m"
    memory_request   = "512Mi"
    cpu_limit        = "500m"
    memory_limit     = "1Gi"
    rate_limiting_enabled = true
    rate_limit_per_minute = 600
  }
}

# =========================================
# Security Variables
# =========================================

variable "jwt_token_expiry_seconds" {
  description = "JWT token expiry in seconds (60 minutes)"
  type        = number
  default     = 3600
}

variable "jwt_refresh_token_expiry_seconds" {
  description = "JWT refresh token expiry in seconds (7 days)"
  type        = number
  default     = 604800
}

variable "jwt_algorithm" {
  description = "JWT signing algorithm"
  type        = string
  default     = "RS256"
}

variable "enable_field_level_encryption" {
  description = "Enable field-level encryption for PII data"
  type        = bool
  default     = true
}

variable "encryption_key_rotation_days" {
  description = "Number of days between encryption key rotations"
  type        = number
  default     = 90
}

# =========================================
# Monitoring Variables
# =========================================

variable "enable_monitoring" {
  description = "Enable monitoring infrastructure"
  type        = bool
  default     = true
}

variable "monitoring_provider" {
  description = "Monitoring provider to use (datadog or prometheus)"
  type        = string
  default     = "datadog"
  validation {
    condition     = contains(["datadog", "prometheus"], var.monitoring_provider)
    error_message = "Monitoring provider must be one of: datadog, prometheus."
  }
}

variable "metrics_retention_days" {
  description = "Number of days to retain metrics data"
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "Number of days to retain log data"
  type        = number
  default     = 30
}

variable "enable_alerting" {
  description = "Enable alerting for monitoring"
  type        = bool
  default     = true
}

variable "alert_notification_channels" {
  description = "List of notification channels for alerts"
  type        = list(string)
  default     = ["email", "slack"]
}

# =========================================
# Performance Variables
# =========================================

variable "application_processing_sla_seconds" {
  description = "Target SLA for application processing in seconds (5 minutes)"
  type        = number
  default     = 300
}

variable "ocr_accuracy_target_percent" {
  description = "Target accuracy percentage for OCR extraction"
  type        = number
  default     = 99
}

variable "automation_rate_target_percent" {
  description = "Target automation rate percentage"
  type        = number
  default     = 93
}

variable "system_uptime_target_percent" {
  description = "Target system uptime percentage"
  type        = number
  default     = 99.9
}

# =========================================
# Tags and Metadata
# =========================================

variable "default_tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default     = {
    Project     = "MCA Application Processing"
    Environment = "development"
    Terraform   = "true"
    Owner       = "Dollar Funding"
  }
}