# -----------------------------------------------
# S3 Storage Infrastructure for MCA Application Processing System
# -----------------------------------------------
# This file initializes the storage module with environment-specific settings
# for the MCA Application Processing System. It configures provider settings,
# backend configuration, and imports the storage module from the modules directory.
# -----------------------------------------------

# -----------------------------------------------
# Terraform Settings
# -----------------------------------------------

terraform {
  # Require Terraform version 1.5.0 or higher for stability and feature support
  required_version = ">= 1.5.0, < 2.0.0"

  # Define required providers with version constraints
  required_providers {
    # AWS provider for S3-compatible storage
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0, < 6.0.0"
    }
  }

  # Backend configuration for state management
  # Using S3 backend for state storage with DynamoDB for locking
  backend "s3" {
    # These values are typically provided via -backend-config options during terraform init
    # or through environment-specific backend configuration files
    key            = "storage/terraform.tfstate"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# -----------------------------------------------
# Provider Configuration
# -----------------------------------------------

# Primary region provider
provider "aws" {
  region = local.primary_region
  
  # Default tags applied to all resources
  default_tags {
    tags = merge(var.tags, {
      Project     = "mca"
      Environment = var.environment
      ManagedBy   = "terraform"
      Component   = "storage"
    })
  }
}

# Replica region provider for disaster recovery
provider "aws" {
  alias  = "replica_region"
  region = local.replica_region
  
  # Default tags applied to all resources in replica region
  default_tags {
    tags = merge(var.tags, {
      Project     = "mca"
      Environment = var.environment
      ManagedBy   = "terraform"
      Component   = "storage-replica"
    })
  }
}

# -----------------------------------------------
# Local Variables
# -----------------------------------------------

locals {
  # Environment-specific settings
  env_config = {
    production = {
      primary_region   = var.aws_region
      replica_regions  = var.enable_replication ? [var.replication_region] : []
      enable_replication = var.enable_replication
      minimum_retention_days = var.minimum_retention_days
      transition_to_ia_days = var.transition_to_ia_days
      transition_to_glacier_days = var.transition_to_glacier_days
      expiration_days = var.expiration_days
      enable_versioning = var.enable_versioning
      enable_encryption = var.enable_encryption
      encryption_algorithm = var.encryption_algorithm
      block_public_access = var.block_public_access
      enable_request_metrics = var.enable_request_metrics
      enable_object_level_logging = var.enable_object_level_logging
    },
    staging = {
      primary_region   = var.aws_region
      replica_regions  = var.enable_replication ? [var.replication_region] : []
      enable_replication = var.enable_replication
      minimum_retention_days = var.minimum_retention_days
      transition_to_ia_days = var.transition_to_ia_days
      transition_to_glacier_days = var.transition_to_glacier_days
      expiration_days = var.expiration_days
      enable_versioning = var.enable_versioning
      enable_encryption = var.enable_encryption
      encryption_algorithm = var.encryption_algorithm
      block_public_access = var.block_public_access
      enable_request_metrics = var.enable_request_metrics
      enable_object_level_logging = var.enable_object_level_logging
    },
    development = {
      primary_region   = var.aws_region
      replica_regions  = []
      enable_replication = false
      minimum_retention_days = var.minimum_retention_days
      transition_to_ia_days = var.transition_to_ia_days
      transition_to_glacier_days = 0
      expiration_days = var.expiration_days
      enable_versioning = var.enable_versioning
      enable_encryption = var.enable_encryption
      encryption_algorithm = var.encryption_algorithm
      block_public_access = var.block_public_access
      enable_request_metrics = var.enable_request_metrics
      enable_object_level_logging = var.enable_object_level_logging
    }
  }
  
  # Set current environment configuration
  current_env_config = local.env_config[var.environment]
  
  # Extract region settings
  primary_region = local.current_env_config.primary_region
  replica_region = length(local.current_env_config.replica_regions) > 0 ? local.current_env_config.replica_regions[0] : local.primary_region
  
  # Environment-specific tags
  env_tags = {
    production = var.production_tags
    staging = var.staging_tags
    development = {}
  }
  
  # Common tags for all resources
  common_tags = merge(var.tags, {
    Project     = "mca"
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "storage"
  })
}

# -----------------------------------------------
# Data Sources
# -----------------------------------------------

# Get current AWS account ID for IAM policies
data "aws_caller_identity" "current" {}

# Get current AWS region for resource creation
data "aws_region" "current" {}

# -----------------------------------------------
# Storage Module
# -----------------------------------------------

module "storage" {
  source = "../modules/storage"
  
  # Pass providers explicitly
  providers = {
    aws              = aws
    aws.replica_region = aws.replica_region
  }
  
  # Environment configuration
  environment = var.environment
  project     = "mca"
  
  # Region configuration
  primary_region   = local.primary_region
  replica_regions  = local.current_env_config.replica_regions
  enable_replication = local.current_env_config.enable_replication
  
  # Bucket configuration
  bucket_name   = "documents"
  bucket_prefix = "dollarfunding"
  enable_versioning = local.current_env_config.enable_versioning
  force_destroy = var.force_destroy
  
  # Security configuration
  enable_encryption = local.current_env_config.enable_encryption
  encryption_algorithm = local.current_env_config.encryption_algorithm  # AES-256 encryption as specified in requirements
  block_public_access = local.current_env_config.block_public_access
  enable_ssl_requests = true
  signed_url_expiration = var.signed_url_expiration * 60  # Convert minutes to seconds
  
  # Lifecycle configuration
  enable_lifecycle_rules = var.enable_lifecycle_rules
  minimum_retention_days = local.current_env_config.minimum_retention_days
  standard_transition_days = local.current_env_config.transition_to_ia_days
  glacier_transition_days = local.current_env_config.transition_to_glacier_days
  expiration_days = local.current_env_config.expiration_days
  archive_storage_class = "STANDARD_IA"  # Infrequent Access for archives
  
  # Object lock configuration (for compliance)
  enable_object_lock = var.environment == "production" ? true : false
  object_lock_mode = "GOVERNANCE"
  object_lock_retention_days = var.minimum_retention_days
  
  # Intelligent tiering configuration
  enable_intelligent_tiering = var.environment == "production" ? true : false
  intelligent_tiering_days_until_archive = var.transition_to_ia_days
  
  # Logging and monitoring configuration
  enable_access_logging = true
  access_log_bucket = var.access_logs_bucket
  access_log_prefix = var.access_logs_prefix
  enable_request_metrics = local.current_env_config.enable_request_metrics
  
  # CORS configuration (disabled by default)
  enable_cors = false
  
  # Transfer acceleration (disabled by default)
  enable_transfer_acceleration = false
  
  # Notification configuration (disabled by default)
  enable_notifications = false
}