# =============================================================================
# Global Terraform Configuration for MCA Application Processing System
# =============================================================================
# This file defines global resources shared across all environments (dev, staging, prod)
# It establishes the foundational infrastructure components needed by all environments
# =============================================================================

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0"
    }
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.10.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0"
    }
  }

  # Remote state configuration for Terraform
  # This ensures state is stored securely and can be shared across team members
  backend "s3" {
    bucket         = "dollarfunding-terraform-state"
    key            = "global/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# Provider configurations
# Note: Credentials should be provided via environment variables or instance profiles
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "MCA-Application-System"
      Environment = "global"
      ManagedBy   = "Terraform"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# =============================================================================
# Global Variables
# =============================================================================

variable "aws_region" {
  description = "The AWS region to deploy global resources"
  type        = string
  default     = "us-east-1"
}

variable "gcp_project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "The GCP region to deploy global resources"
  type        = string
  default     = "us-central1"
}

variable "azure_location" {
  description = "The Azure location to deploy global resources"
  type        = string
  default     = "eastus"
}

# =============================================================================
# Global Resources - Terraform State Management
# =============================================================================

# This module creates the S3 bucket and DynamoDB table for Terraform state management
module "terraform_state" {
  source = "../modules/terraform-state"

  state_bucket_name = "dollarfunding-terraform-state"
  lock_table_name   = "terraform-locks"
  
  # Enable versioning for disaster recovery (RPO: 24h, RTO: <1h)
  enable_versioning = true
  
  # Lifecycle rules for state management
  lifecycle_rules = [
    {
      id      = "expire-old-versions"
      enabled = true
      
      noncurrent_version_expiration = {
        days = 90
      }
    }
  ]
}

# =============================================================================
# Global Resources - Container Registry
# =============================================================================

# Container registry for storing Docker images across all environments
module "container_registry" {
  source = "../modules/container-registry"
  
  registry_name = "dollarfunding-mca"
  
  # Image scanning configuration
  enable_vulnerability_scanning = true
  scan_on_push                 = true
  
  # Image lifecycle policies
  lifecycle_policy = {
    keep_latest_images_count = 10
    untagged_image_expiration_days = 30
  }
  
  # Cross-region replication for disaster recovery
  enable_replication = true
  replica_regions    = ["us-west-2"]
}

# =============================================================================
# Global Resources - Shared Storage
# =============================================================================

# S3 buckets for document storage with appropriate security controls
module "document_storage" {
  source = "../modules/s3-storage"
  
  # Production bucket
  production_bucket_name = "mca-documents-production"
  # Staging bucket
  staging_bucket_name    = "mca-documents-staging"
  # Development bucket
  development_bucket_name = "mca-documents-development"
  
  # Security configuration
  enable_encryption     = true
  encryption_algorithm  = "AES256"
  block_public_access   = true
  
  # Versioning for document history
  enable_versioning     = true
  
  # Lifecycle policies for cost optimization
  lifecycle_rules = [
    {
      id      = "transition-to-ia"
      enabled = true
      
      transition = {
        days          = 30
        storage_class = "STANDARD_IA"
      }
    }
  ]
}

# =============================================================================
# Global Resources - Monitoring
# =============================================================================

# Monitoring infrastructure shared across environments
module "monitoring" {
  source = "../modules/monitoring"
  
  # Datadog configuration
  datadog_enabled = true
  metrics_retention_months = 15
  
  # Alerting configuration
  alert_channels = {
    email = ["operations@dollarfunding.com"]
    slack = ["#mca-alerts"]
  }
  
  # Dashboard configuration
  create_default_dashboards = true
  
  # Log management
  log_retention_days = 30
}

# =============================================================================
# Global Resources - IAM and Security
# =============================================================================

# IAM roles and policies for cross-environment access
module "iam" {
  source = "../modules/security/iam"
  
  # CI/CD service roles
  create_cicd_roles = true
  
  # Cross-account access roles (if applicable)
  enable_cross_account_access = false
  
  # Security audit roles
  create_security_audit_role = true
}

# =============================================================================
# Global Resources - Network
# =============================================================================

# VPC peering and transit gateway configurations (if applicable)
module "network" {
  source = "../modules/network/global"
  
  # Transit gateway configuration
  create_transit_gateway = false
  
  # VPC peering configuration
  enable_vpc_peering = false
}

# =============================================================================
# Outputs
# =============================================================================

output "terraform_state_bucket" {
  description = "The S3 bucket used for Terraform state storage"
  value       = module.terraform_state.bucket_name
}

output "terraform_lock_table" {
  description = "The DynamoDB table used for Terraform state locking"
  value       = module.terraform_state.lock_table_name
}

output "container_registry_url" {
  description = "The URL of the container registry"
  value       = module.container_registry.registry_url
}

output "document_storage_buckets" {
  description = "The S3 buckets created for document storage"
  value = {
    production  = module.document_storage.production_bucket_name
    staging     = module.document_storage.staging_bucket_name
    development = module.document_storage.development_bucket_name
  }
}