# Staging Environment Variables
# This file defines all input variables for the staging environment Terraform configuration

# ---------------------------------------------------------------------------------------------------------------------
# GENERAL CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "mca-application"
}

# ---------------------------------------------------------------------------------------------------------------------
# CLOUD PROVIDER CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

variable "cloud_provider" {
  description = "Cloud provider to use (aws, azure, gcp)"
  type        = string
  default     = "aws"
  validation {
    condition     = contains(["aws", "azure", "gcp"], var.cloud_provider)
    error_message = "Valid values for cloud_provider are: aws, azure, gcp."
  }
}

variable "region" {
  description = "Cloud provider region"
  type        = string
  default     = "us-east-1" # Default AWS region, override for other providers
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"] # Default AWS AZs, override for other providers
}

# ---------------------------------------------------------------------------------------------------------------------
# KUBERNETES CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

variable "kubernetes_version" {
  description = "Kubernetes version to use"
  type        = string
  default     = "1.25"
}

variable "node_instance_types" {
  description = "Map of node pool names to instance types"
  type        = map(string)
  default = {
    "general"  = "t3.large"    # General purpose nodes
    "memory"   = "r5.large"    # Memory-optimized nodes for Redis
    "compute"  = "c5.large"    # Compute-optimized nodes for processing
    "gpu"      = "g4dn.xlarge" # GPU nodes for OCR service
  }
}

variable "node_counts" {
  description = "Map of node pool names to desired counts"
  type        = map(number)
  default = {
    "general"  = 2 # General purpose nodes
    "memory"   = 2 # Memory-optimized nodes
    "compute"  = 2 # Compute-optimized nodes
    "gpu"      = 1 # GPU nodes (fewer in staging than production)
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# DATABASE CONFIGURATION (PostgreSQL)
# ---------------------------------------------------------------------------------------------------------------------

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "14"
}

variable "postgres_instance_class" {
  description = "PostgreSQL instance class"
  type        = string
  default     = "db.m5.large" # Smaller instance for staging compared to production
}

variable "postgres_storage" {
  description = "PostgreSQL allocated storage in GB"
  type        = number
  default     = 100
}

variable "postgres_iops" {
  description = "PostgreSQL provisioned IOPS"
  type        = number
  default     = 1000 # As specified in the technical spec
}

variable "postgres_multi_az" {
  description = "Enable Multi-AZ deployment for PostgreSQL"
  type        = bool
  default     = true # As specified in the technical spec
}

variable "postgres_read_replicas" {
  description = "Number of PostgreSQL read replicas"
  type        = number
  default     = 1 # 1 read replica for staging as specified in the technical spec
}

variable "postgres_backup_retention_period" {
  description = "PostgreSQL backup retention period in days"
  type        = number
  default     = 30 # As specified in the technical spec
}

variable "postgres_connection_pool_min" {
  description = "Minimum connections in the PostgreSQL connection pool"
  type        = number
  default     = 10 # As specified in the technical spec
}

variable "postgres_connection_pool_max" {
  description = "Maximum connections in the PostgreSQL connection pool"
  type        = number
  default     = 50 # As specified in the technical spec
}

# ---------------------------------------------------------------------------------------------------------------------
# MESSAGING CONFIGURATION (RabbitMQ)
# ---------------------------------------------------------------------------------------------------------------------

variable "rabbitmq_version" {
  description = "RabbitMQ version"
  type        = string
  default     = "3.10"
}

variable "rabbitmq_instance_type" {
  description = "RabbitMQ instance type"
  type        = string
  default     = "m5.large" # Appropriate for staging workloads
}

variable "rabbitmq_nodes" {
  description = "Number of RabbitMQ nodes in the cluster"
  type        = number
  default     = 3 # 3-node minimum as specified in the technical spec
}

variable "rabbitmq_exchanges" {
  description = "List of RabbitMQ exchanges to create"
  type        = list(object({
    name       = string
    type       = string
    durable    = bool
    auto_delete = bool
  }))
  default = [
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
  default = [
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

# ---------------------------------------------------------------------------------------------------------------------
# CACHE CONFIGURATION (Redis)
# ---------------------------------------------------------------------------------------------------------------------

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "7.0"
}

variable "redis_instance_type" {
  description = "Redis instance type"
  type        = string
  default     = "cache.m5.large" # Appropriate for staging workloads
}

variable "redis_shards" {
  description = "Number of Redis shards"
  type        = number
  default     = 3 # 3+ shards as specified in the technical spec
}

variable "redis_replicas_per_shard" {
  description = "Number of replicas per Redis shard"
  type        = number
  default     = 1 # At least 1 replica per shard as specified in the technical spec
}

variable "redis_snapshot_frequency" {
  description = "Redis snapshot frequency in minutes"
  type        = number
  default     = 60 # 60 minutes as specified in the technical spec
}

variable "redis_ttl_settings" {
  description = "TTL settings for different Redis data types"
  type        = map(number)
  default = {
    "application_data" = 900  # 15 minutes in seconds
    "user_sessions"    = 86400 # 24 hours in seconds
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# STORAGE CONFIGURATION (S3-compatible)
# ---------------------------------------------------------------------------------------------------------------------

variable "s3_bucket_name" {
  description = "S3 bucket name for document storage"
  type        = string
  default     = "mca-documents-staging" # As specified in the technical spec
}

variable "s3_versioning_enabled" {
  description = "Enable versioning for S3 bucket"
  type        = bool
  default     = true # As specified in the technical spec
}

variable "s3_encryption_enabled" {
  description = "Enable server-side encryption for S3 bucket"
  type        = bool
  default     = true # AES-256 encryption as specified in the technical spec
}

variable "s3_signed_url_expiration" {
  description = "Expiration time for signed URLs in seconds"
  type        = number
  default     = 900 # 15 minutes as specified in the technical spec
}

# ---------------------------------------------------------------------------------------------------------------------
# CONTAINER REGISTRY CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

variable "container_registry_type" {
  description = "Type of container registry to use (ecr, acr, gcr, harbor)"
  type        = string
  default     = "ecr" # Default to AWS ECR, override for other providers
  validation {
    condition     = contains(["ecr", "acr", "gcr", "harbor"], var.container_registry_type)
    error_message = "Valid values for container_registry_type are: ecr, acr, gcr, harbor."
  }
}

variable "container_registry_retention_count" {
  description = "Number of container images to retain per repository"
  type        = number
  default     = 10 # Keep latest 10 plus tagged releases as specified in the technical spec
}

variable "container_registry_scan_on_push" {
  description = "Enable vulnerability scanning on container image push"
  type        = bool
  default     = true # As specified in the technical spec
}

# ---------------------------------------------------------------------------------------------------------------------
# MONITORING CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

variable "monitoring_system" {
  description = "Monitoring system to use (datadog, prometheus)"
  type        = string
  default     = "prometheus" # Default to self-hosted Prometheus for staging
  validation {
    condition     = contains(["datadog", "prometheus"], var.monitoring_system)
    error_message = "Valid values for monitoring_system are: datadog, prometheus."
  }
}

variable "metrics_retention_days" {
  description = "Number of days to retain metrics"
  type        = number
  default     = 30 # 30 days as specified in the technical spec for Prometheus
}

variable "metrics_scrape_interval" {
  description = "Metrics scrape interval in seconds"
  type        = number
  default     = 15 # 15 seconds as specified in the technical spec for Prometheus
}

# ---------------------------------------------------------------------------------------------------------------------
# FEATURE FLAGS
# ---------------------------------------------------------------------------------------------------------------------

variable "enable_gpu_acceleration" {
  description = "Enable GPU acceleration for OCR service"
  type        = bool
  default     = true # Required as per technical spec
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for Kubernetes node pools"
  type        = bool
  default     = true
}

variable "enable_cross_region_replication" {
  description = "Enable cross-region replication for critical data"
  type        = bool
  default     = false # Not needed for staging environment
}

variable "enable_advanced_monitoring" {
  description = "Enable advanced monitoring features"
  type        = bool
  default     = true
}

# ---------------------------------------------------------------------------------------------------------------------
# EMAIL SERVICE CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

variable "email_imap_server" {
  description = "IMAP server for email monitoring"
  type        = string
  default     = "imap.dollarfunding.com"
}

variable "email_imap_port" {
  description = "IMAP port for email monitoring"
  type        = number
  default     = 993 # Standard IMAPS port
}

variable "email_poll_interval" {
  description = "Email polling interval in seconds"
  type        = number
  default     = 60 # Check every minute in staging
}

# ---------------------------------------------------------------------------------------------------------------------
# SECURITY CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

variable "jwt_token_expiry" {
  description = "JWT token expiry in minutes"
  type        = number
  default     = 60 # 60 minutes as specified in the technical spec
}

variable "jwt_refresh_token_expiry" {
  description = "JWT refresh token expiry in days"
  type        = number
  default     = 7 # 7 days as specified in the technical spec
}

variable "enable_field_level_encryption" {
  description = "Enable field-level encryption for PII"
  type        = bool
  default     = true # As specified in the technical spec
}

variable "api_rate_limit" {
  description = "API rate limit in requests per minute"
  type        = number
  default     = 300 # Appropriate for staging environment
}