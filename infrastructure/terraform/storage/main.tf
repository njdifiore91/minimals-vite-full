# Main Terraform configuration file for S3-compatible storage infrastructure
# This file initializes the storage module with environment-specific settings

terraform {
  # Backend configuration will be provided by environment-specific backend.tf files
  # Uses S3 for state storage with DynamoDB for state locking
  backend "s3" {}

  # Required providers with version constraints
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}

# Provider configuration
provider "aws" {
  region = var.region

  # Default tags applied to all resources
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "MCA Application Processing System"
      ManagedBy   = "Terraform"
      Service     = "Document Storage"
      SecurityCompliance = "AES256-Encrypted"
    }
  }
}

# Local variables for configuration
locals {
  # Bucket names with environment prefix
  production_bucket_name = "mca-documents-production"
  staging_bucket_name    = "mca-documents-staging"
  
  # Common tags for all storage resources
  common_tags = {
    Application = "MCA Application Processing System"
    Component   = "Document Storage"
    DataClassification = "Confidential"
    Compliance = "GDPR-PII"
  }
  
  # Access control settings
  bucket_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowOnlyAuthorizedServices"
        Effect    = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/MCADocumentProcessingRole"
        }
        Action    = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource  = [
          "arn:aws:s3:::${var.environment == "production" ? local.production_bucket_name : local.staging_bucket_name}",
          "arn:aws:s3:::${var.environment == "production" ? local.production_bucket_name : local.staging_bucket_name}/*"
        ]
      }
    ]
  })
}

# Data sources for environment-specific configurations
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Import storage module with environment-specific settings
module "storage" {
  source = "../modules/storage"

  # Environment configuration
  environment         = var.environment
  region              = var.region
  replica_region      = var.replica_region
  
  # Bucket configuration
  production_bucket_name = local.production_bucket_name
  staging_bucket_name    = local.staging_bucket_name
  
  # Security configuration
  enable_encryption      = true
  encryption_algorithm   = "AES256"  # Server-side encryption for all objects
  enable_versioning      = true      # Enable versioning for document history tracking
  bucket_policy          = local.bucket_policy  # Apply bucket policy to restrict access
  
  # Lifecycle configuration
  lifecycle_rules_enabled = true
  transition_days         = var.transition_days  # Days before transitioning to Infrequent Access
  expiration_days         = var.expiration_days  # Days before expiration (if enabled)
  
  # Replication configuration
  enable_replication     = var.enable_replication  # Cross-region replication for disaster recovery
  
  # Logging and monitoring
  enable_access_logging  = true  # Enable access logging for audit purposes
  enable_request_metrics = true  # Enable request metrics for monitoring
  
  # Access control
  block_public_access    = true  # Block all public access to buckets
  
  # Tags
  tags = merge(local.common_tags, var.additional_tags)
}