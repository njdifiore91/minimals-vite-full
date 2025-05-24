# =============================================================================
# Global Terraform Variables for Dollar Funding MCA Application
# =============================================================================
# This file defines all input variables for the global Terraform configuration,
# including organization name, environment tags, DNS settings, and global
# resource naming conventions.
# =============================================================================

# -----------------------------------------------------------------------------
# Organization Information
# -----------------------------------------------------------------------------

variable "organization" {
  description = "Organization name used in resource naming and tagging"
  type        = string
  default     = "dollarfunding"
}

variable "organization_id" {
  description = "Organization identifier used for resource naming and tagging"
  type        = string
  default     = "df"
}

variable "project" {
  description = "Project name used in resource naming and tagging"
  type        = string
  default     = "mca"
}

variable "project_full_name" {
  description = "Full project name for documentation and extended tagging"
  type        = string
  default     = "Merchant Cash Advance"
}

# -----------------------------------------------------------------------------
# Environment Configuration
# -----------------------------------------------------------------------------

variable "environments" {
  description = "List of valid environments for deployment"
  type        = list(string)
  default     = ["development", "staging", "production"]
}

variable "environment_short_names" {
  description = "Short names for environments used in resource naming"
  type        = map(string)
  default     = {
    development = "dev"
    staging     = "stg"
    production  = "prod"
  }
}

variable "environment_configs" {
  description = "Configuration parameters for each environment"
  type        = map(object({
    is_production  = bool
    instance_size  = string
    replica_count  = number
    backup_enabled = bool
    multi_az       = bool
  }))
  default     = {
    development = {
      is_production  = false
      instance_size  = "small"
      replica_count  = 0
      backup_enabled = false
      multi_az       = false
    }
    staging = {
      is_production  = false
      instance_size  = "medium"
      replica_count  = 1
      backup_enabled = true
      multi_az       = true
    }
    production = {
      is_production  = true
      instance_size  = "large"
      replica_count  = 2
      backup_enabled = true
      multi_az       = true
    }
  }
}

# -----------------------------------------------------------------------------
# DNS Configuration
# -----------------------------------------------------------------------------

variable "domain_name" {
  description = "Primary domain name for the application"
  type        = string
  default     = "dollarfunding.com"
}

variable "dns_ttl" {
  description = "Default TTL for DNS records in seconds"
  type        = number
  default     = 300
}

variable "environment_domains" {
  description = "Domain names for each environment"
  type        = map(string)
  default     = {
    development = "dev.dollarfunding.com"
    staging     = "staging.dollarfunding.com"
    production  = "dollarfunding.com"
  }
}

variable "enable_www_redirect" {
  description = "Enable redirection from www subdomain to apex domain"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Regional Configuration
# -----------------------------------------------------------------------------

variable "primary_region" {
  description = "Primary AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "secondary_region" {
  description = "Secondary AWS region for disaster recovery"
  type        = string
  default     = "us-west-2"
}

variable "multi_region_enabled" {
  description = "Enable multi-region deployment for disaster recovery"
  type        = bool
  default     = true
}

variable "region_configs" {
  description = "Configuration for each supported region"
  type        = map(object({
    short_name = string
    full_name  = string
  }))
  default     = {
    "us-east-1" = {
      short_name = "use1"
      full_name  = "US East (N. Virginia)"
    }
    "us-west-2" = {
      short_name = "usw2"
      full_name  = "US West (Oregon)"
    }
  }
}

# -----------------------------------------------------------------------------
# Resource Naming Conventions
# -----------------------------------------------------------------------------

variable "resource_prefix" {
  description = "Prefix to be applied to all resource names"
  type        = string
  default     = "df-mca"
}

variable "naming_convention" {
  description = "Naming convention pattern for resources"
  type        = string
  default     = "{prefix}-{env}-{region}-{resource}-{suffix}"
}

variable "resource_type_abbreviations" {
  description = "Abbreviations for resource types used in naming"
  type        = map(string)
  default     = {
    "postgresql"      = "pg"
    "rabbitmq"        = "rmq"
    "redis"           = "redis"
    "s3"              = "s3"
    "kubernetes"      = "k8s"
    "security_group"  = "sg"
    "load_balancer"   = "lb"
    "virtual_network" = "vnet"
    "subnet"          = "snet"
  }
}

# -----------------------------------------------------------------------------
# Tagging Configuration
# -----------------------------------------------------------------------------

variable "mandatory_tags" {
  description = "Mandatory tags to be applied to all resources"
  type        = map(string)
  default     = {
    "ManagedBy" = "Terraform"
    "Project"   = "MCA"
  }
}

variable "environment_tags" {
  description = "Environment-specific tags"
  type        = map(map(string))
  default     = {
    development = {
      "Environment" = "Development"
      "CostCenter" = "DevOps"
    }
    staging = {
      "Environment" = "Staging"
      "CostCenter" = "DevOps"
    }
    production = {
      "Environment" = "Production"
      "CostCenter" = "Operations"
    }
  }
}

variable "backup_tags" {
  description = "Tags for backup-enabled resources"
  type        = map(string)
  default     = {
    "Backup"          = "true"
    "BackupSchedule"  = "daily"
    "RetentionPeriod" = "30days"
  }
}

# -----------------------------------------------------------------------------
# Global Resource Configuration
# -----------------------------------------------------------------------------

variable "terraform_state_bucket" {
  description = "S3 bucket name for Terraform state storage"
  type        = string
  default     = "df-mca-terraform-state"
}

variable "terraform_state_lock_table" {
  description = "DynamoDB table name for Terraform state locking"
  type        = string
  default     = "df-mca-terraform-state-lock"
}

variable "terraform_state_key_prefix" {
  description = "Key prefix for Terraform state files"
  type        = string
  default     = "global"
}

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------

variable "postgresql_version" {
  description = "PostgreSQL version to be used across all environments"
  type        = string
  default     = "14"
}

variable "postgresql_parameters" {
  description = "Global PostgreSQL parameters to be applied to all instances"
  type        = map(string)
  default     = {
    "max_connections"                  = "100"
    "shared_buffers"                   = "4GB"
    "effective_cache_size"             = "12GB"
    "maintenance_work_mem"             = "1GB"
    "checkpoint_completion_target"     = "0.9"
    "wal_buffers"                      = "16MB"
    "default_statistics_target"        = "100"
    "random_page_cost"                 = "1.1"
    "effective_io_concurrency"         = "200"
    "work_mem"                         = "41943kB"
    "min_wal_size"                     = "1GB"
    "max_wal_size"                     = "4GB"
    "max_worker_processes"             = "8"
    "max_parallel_workers_per_gather"  = "4"
    "max_parallel_workers"             = "8"
    "max_parallel_maintenance_workers" = "4"
  }
}

# -----------------------------------------------------------------------------
# Redis Configuration
# -----------------------------------------------------------------------------

variable "redis_version" {
  description = "Redis version to be used across all environments"
  type        = string
  default     = "7.0"
}

variable "redis_parameters" {
  description = "Global Redis parameters to be applied to all instances"
  type        = map(string)
  default     = {
    "maxmemory-policy"      = "allkeys-lru"
    "notify-keyspace-events" = "Ex"
    "timeout"               = "300"
    "tcp-keepalive"         = "60"
  }
}

# -----------------------------------------------------------------------------
# RabbitMQ Configuration
# -----------------------------------------------------------------------------

variable "rabbitmq_version" {
  description = "RabbitMQ version to be used across all environments"
  type        = string
  default     = "3.10"
}

variable "rabbitmq_exchanges" {
  description = "Global RabbitMQ exchanges to be created in all environments"
  type        = list(object({
    name       = string
    type       = string
    durable    = bool
    auto_delete = bool
  }))
  default     = [
    {
      name        = "mca.documents"
      type        = "fanout"
      durable     = true
      auto_delete = false
    }
  ]
}

variable "rabbitmq_queues" {
  description = "Global RabbitMQ queues to be created in all environments"
  type        = list(object({
    name       = string
    durable    = bool
    auto_delete = bool
  }))
  default     = [
    {
      name        = "document-processing"
      durable     = true
      auto_delete = false
    },
    {
      name        = "data-extraction"
      durable     = true
      auto_delete = false
    },
    {
      name        = "notification"
      durable     = true
      auto_delete = false
    }
  ]
}

# -----------------------------------------------------------------------------
# S3 Storage Configuration
# -----------------------------------------------------------------------------

variable "s3_bucket_names" {
  description = "S3 bucket names for each environment"
  type        = map(string)
  default     = {
    development = "mca-documents-development"
    staging     = "mca-documents-staging"
    production  = "mca-documents-production"
  }
}

variable "s3_lifecycle_rules" {
  description = "Lifecycle rules for S3 buckets"
  type        = list(object({
    id                                     = string
    enabled                                = bool
    prefix                                 = string
    expiration_days                        = number
    noncurrent_version_expiration_days     = number
    transition_days                        = number
    transition_storage_class               = string
    noncurrent_version_transition_days     = number
    noncurrent_version_transition_storage_class = string
  }))
  default     = [
    {
      id                                     = "archive-rule"
      enabled                                = true
      prefix                                 = "archive/"
      expiration_days                        = 0
      noncurrent_version_expiration_days     = 90
      transition_days                        = 30
      transition_storage_class               = "STANDARD_IA"
      noncurrent_version_transition_days     = 30
      noncurrent_version_transition_storage_class = "STANDARD_IA"
    }
  ]
}

# -----------------------------------------------------------------------------
# Security Configuration
# -----------------------------------------------------------------------------

variable "kms_key_rotation_enabled" {
  description = "Enable automatic rotation of KMS keys"
  type        = bool
  default     = true
}

variable "kms_key_deletion_window_in_days" {
  description = "Waiting period before KMS key deletion"
  type        = number
  default     = 30
}

variable "ssl_certificate_domains" {
  description = "Domains for which SSL certificates should be provisioned"
  type        = list(string)
  default     = ["dollarfunding.com", "*.dollarfunding.com"]
}