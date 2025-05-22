# Production Environment Variables for MCA Application Processing System
# This file defines all input variables for the production Terraform configuration

# -----------------------------------------------------------------------------
# Cloud Provider Configuration
# -----------------------------------------------------------------------------

variable "cloud_provider" {
  description = "The cloud provider to deploy infrastructure to (aws, azure, gcp)"
  type        = string
  default     = "aws"
  validation {
    condition     = contains(["aws", "azure", "gcp"], var.cloud_provider)
    error_message = "Valid values for cloud_provider are: aws, azure, gcp"
  }
}

variable "region" {
  description = "The primary region for infrastructure deployment"
  type        = string
  default     = "us-east-1" # Default AWS region, will be ignored for other providers
}

variable "secondary_region" {
  description = "The secondary region for disaster recovery and multi-region resources"
  type        = string
  default     = "us-west-2" # Default AWS secondary region, will be ignored for other providers
}

variable "availability_zones" {
  description = "List of availability zones to use within the region"
  type        = list(string)
  default     = ["a", "b", "c"] # Will be combined with region to form AZs like us-east-1a
}

# -----------------------------------------------------------------------------
# Environment Configuration
# -----------------------------------------------------------------------------

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "mca"
}

variable "domain_name" {
  description = "Base domain name for the application"
  type        = string
  default     = "dollarfunding.com"
}

variable "enable_disaster_recovery" {
  description = "Enable disaster recovery features like cross-region replication"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Database Configuration (PostgreSQL)
# -----------------------------------------------------------------------------

variable "postgres_version" {
  description = "PostgreSQL version to deploy"
  type        = string
  default     = "14"
}

variable "postgres_instance_class" {
  description = "Instance class for PostgreSQL database"
  type        = string
  default     = "db.m5.xlarge" # Production-grade instance with good performance
}

variable "postgres_allocated_storage" {
  description = "Allocated storage for PostgreSQL in GB"
  type        = number
  default     = 100
}

variable "postgres_iops" {
  description = "Provisioned IOPS for PostgreSQL"
  type        = number
  default     = 1000 # As specified in the technical spec
}

variable "postgres_multi_az" {
  description = "Enable Multi-AZ deployment for PostgreSQL"
  type        = bool
  default     = true
}

variable "postgres_read_replicas" {
  description = "Number of read replicas for PostgreSQL"
  type        = number
  default     = 2 # As specified in the technical spec for production
}

variable "postgres_backup_retention_period" {
  description = "Backup retention period in days for PostgreSQL"
  type        = number
  default     = 30 # As specified in the technical spec
}

variable "postgres_deletion_protection" {
  description = "Enable deletion protection for PostgreSQL"
  type        = bool
  default     = true
}

variable "postgres_min_connections" {
  description = "Minimum number of database connections in the pool"
  type        = number
  default     = 10 # As specified in the technical spec
}

variable "postgres_max_connections" {
  description = "Maximum number of database connections in the pool"
  type        = number
  default     = 50 # As specified in the technical spec
}

# -----------------------------------------------------------------------------
# Messaging Configuration (RabbitMQ)
# -----------------------------------------------------------------------------

variable "rabbitmq_version" {
  description = "RabbitMQ version to deploy"
  type        = string
  default     = "3.10"
}

variable "rabbitmq_instance_type" {
  description = "Instance type for RabbitMQ nodes"
  type        = string
  default     = "m5.large" # Production-grade instance
}

variable "rabbitmq_cluster_size" {
  description = "Number of nodes in the RabbitMQ cluster"
  type        = number
  default     = 3 # Minimum for high availability as specified
}

variable "rabbitmq_enable_mirroring" {
  description = "Enable queue mirroring for RabbitMQ"
  type        = bool
  default     = true
}

variable "rabbitmq_enable_persistent_storage" {
  description = "Enable persistent storage for RabbitMQ"
  type        = bool
  default     = true
}

variable "rabbitmq_storage_size" {
  description = "Storage size for RabbitMQ persistent volumes in GB"
  type        = number
  default     = 50
}

variable "rabbitmq_exchanges" {
  description = "List of RabbitMQ exchanges to create"
  type        = list(string)
  default     = ["mca.documents"]
}

variable "rabbitmq_queues" {
  description = "List of RabbitMQ queues to create"
  type        = list(string)
  default     = ["document-processing", "data-extraction", "notification"]
}

# -----------------------------------------------------------------------------
# Cache Configuration (Redis)
# -----------------------------------------------------------------------------

variable "redis_version" {
  description = "Redis version to deploy"
  type        = string
  default     = "7.0"
}

variable "redis_instance_type" {
  description = "Instance type for Redis nodes"
  type        = string
  default     = "cache.m5.large" # Production-grade instance
}

variable "redis_cluster_enabled" {
  description = "Enable Redis cluster mode"
  type        = bool
  default     = true
}

variable "redis_num_shards" {
  description = "Number of shards in the Redis cluster"
  type        = number
  default     = 3 # Minimum for production as specified
}

variable "redis_replicas_per_shard" {
  description = "Number of replicas per shard in the Redis cluster"
  type        = number
  default     = 1 # Minimum for production as specified
}

variable "redis_auto_failover" {
  description = "Enable auto-failover for Redis"
  type        = bool
  default     = true
}

variable "redis_snapshot_retention" {
  description = "Number of days to retain Redis snapshots"
  type        = number
  default     = 7
}

variable "redis_data_tiering" {
  description = "Enable data tiering for Redis"
  type        = bool
  default     = true
}

variable "redis_data_ttl" {
  description = "TTL for application data in Redis (in minutes)"
  type        = number
  default     = 15 # As specified in the technical spec
}

variable "redis_session_ttl" {
  description = "TTL for session data in Redis (in hours)"
  type        = number
  default     = 24 # As specified in the technical spec
}

# -----------------------------------------------------------------------------
# Storage Configuration (S3-compatible)
# -----------------------------------------------------------------------------

variable "s3_bucket_name" {
  description = "Base name for S3 buckets (will be prefixed with environment)"
  type        = string
  default     = "mca-documents"
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
  description = "Encryption algorithm for S3 buckets"
  type        = string
  default     = "AES256" # As specified in the technical spec
}

variable "s3_enable_cross_region_replication" {
  description = "Enable cross-region replication for S3 buckets"
  type        = bool
  default     = true
}

variable "s3_lifecycle_rules_enabled" {
  description = "Enable lifecycle rules for S3 buckets"
  type        = bool
  default     = true
}

variable "s3_retention_period" {
  description = "Minimum retention period for objects in days"
  type        = number
  default     = 30 # As specified in the technical spec
}

variable "s3_transition_to_ia_days" {
  description = "Days after which objects transition to Infrequent Access storage class"
  type        = number
  default     = 90
}

variable "s3_signed_url_expiry" {
  description = "Expiration time for signed URLs in minutes"
  type        = number
  default     = 15 # As specified in the technical spec
}

# -----------------------------------------------------------------------------
# Kubernetes Configuration
# -----------------------------------------------------------------------------

variable "kubernetes_version" {
  description = "Kubernetes version to deploy"
  type        = string
  default     = "1.25"
}

variable "kubernetes_node_groups" {
  description = "Configuration for Kubernetes node groups"
  type = map(object({
    instance_type = string
    min_size      = number
    max_size      = number
    desired_size  = number
    disk_size     = number
  }))
  default = {
    general = {
      instance_type = "m5.xlarge"
      min_size      = 3
      max_size      = 10
      desired_size  = 3
      disk_size     = 100
    },
    gpu = {
      instance_type = "g4dn.xlarge" # GPU instance for OCR service
      min_size      = 2
      max_size      = 5
      desired_size  = 2
      disk_size     = 100
    }
  }
}

variable "kubernetes_namespaces" {
  description = "List of Kubernetes namespaces to create"
  type        = list(string)
  default     = ["email-service", "document-service", "ocr-service", "data-service", "notification-service", "api-gateway", "monitoring", "rabbitmq", "redis"]
}

# -----------------------------------------------------------------------------
# Container Registry Configuration
# -----------------------------------------------------------------------------

variable "container_registry_type" {
  description = "Type of container registry to use (ecr, acr, gcr, harbor)"
  type        = string
  default     = "ecr" # Default for AWS
  validation {
    condition     = contains(["ecr", "acr", "gcr", "harbor"], var.container_registry_type)
    error_message = "Valid values for container_registry_type are: ecr, acr, gcr, harbor"
  }
}

variable "container_registry_scan_on_push" {
  description = "Enable vulnerability scanning on image push"
  type        = bool
  default     = true
}

variable "container_registry_retention_count" {
  description = "Number of image versions to retain"
  type        = number
  default     = 10 # As specified in the technical spec
}

variable "container_registry_repositories" {
  description = "List of container repositories to create"
  type        = list(string)
  default     = ["email-service", "document-service", "ocr-service", "data-service", "notification-service", "api-gateway"]
}

# -----------------------------------------------------------------------------
# Monitoring Configuration
# -----------------------------------------------------------------------------

variable "monitoring_solution" {
  description = "Monitoring solution to deploy (datadog, prometheus)"
  type        = string
  default     = "datadog" # As mentioned in the technical spec
  validation {
    condition     = contains(["datadog", "prometheus"], var.monitoring_solution)
    error_message = "Valid values for monitoring_solution are: datadog, prometheus"
  }
}

variable "monitoring_metrics_retention_months" {
  description = "Number of months to retain monitoring metrics"
  type        = number
  default     = 15 # As specified in the technical spec
}

variable "monitoring_collection_interval" {
  description = "Metrics collection interval in seconds"
  type        = number
  default     = 10 # As specified in the technical spec
}

variable "monitoring_log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 90
}

variable "monitoring_enable_apm" {
  description = "Enable Application Performance Monitoring"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------

variable "enable_gpu_acceleration" {
  description = "Enable GPU acceleration for OCR service"
  type        = bool
  default     = true # Required as per technical spec
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for services"
  type        = bool
  default     = true
}

variable "enable_enhanced_security" {
  description = "Enable enhanced security features"
  type        = bool
  default     = true
}

variable "enable_multi_region" {
  description = "Enable multi-region deployment for critical components"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Security Configuration
# -----------------------------------------------------------------------------

variable "jwt_token_expiry_minutes" {
  description = "JWT token expiry time in minutes"
  type        = number
  default     = 60 # As specified in the technical spec
}

variable "jwt_refresh_token_expiry_days" {
  description = "JWT refresh token expiry time in days"
  type        = number
  default     = 7 # As specified in the technical spec
}

variable "jwt_algorithm" {
  description = "JWT signing algorithm"
  type        = string
  default     = "RS256" # As specified in the technical spec
}

variable "enable_field_level_encryption" {
  description = "Enable field-level encryption for PII data"
  type        = bool
  default     = true
}

variable "enable_waf" {
  description = "Enable Web Application Firewall"
  type        = bool
  default     = true
}

variable "enable_ddos_protection" {
  description = "Enable DDoS protection"
  type        = bool
  default     = true
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC flow logs"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# API Gateway Configuration
# -----------------------------------------------------------------------------

variable "api_gateway_type" {
  description = "Type of API Gateway to deploy (kong, aws, azure, gcp)"
  type        = string
  default     = "kong" # As specified in the technical spec
  validation {
    condition     = contains(["kong", "aws", "azure", "gcp"], var.api_gateway_type)
    error_message = "Valid values for api_gateway_type are: kong, aws, azure, gcp"
  }
}

variable "api_rate_limit_per_second" {
  description = "API rate limit per second"
  type        = number
  default     = 100
}

variable "api_enable_caching" {
  description = "Enable API response caching"
  type        = bool
  default     = true
}

variable "api_cache_ttl" {
  description = "API cache TTL in seconds"
  type        = number
  default     = 300
}

variable "api_enable_cors" {
  description = "Enable CORS for API Gateway"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "production"
    Project     = "mca"
    ManagedBy   = "terraform"
  }
}