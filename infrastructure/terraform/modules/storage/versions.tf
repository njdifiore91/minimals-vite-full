# versions.tf for the storage module
# This file specifies Terraform version constraints and required provider versions
# to ensure consistent deployment of the storage infrastructure across different environments.

terraform {
  # Require Terraform version 1.5.0 or higher for stability and feature support
  # This version supports the AWS provider features needed for S3 storage with encryption
  # and multi-region replication capabilities
  required_version = ">= 1.5.0, < 2.0.0"

  # Define required providers with version constraints
  required_providers {
    # AWS provider for S3-compatible storage
    # Version constraint aligns with AWS SDK client-s3 3.509.0 compatibility
    # and ensures support for AES-256 encryption, lifecycle policies, and cross-region replication
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0, < 6.0.0"
      
      # Provider feature flags
      configuration_aliases = [
        # Allow for multi-region replication by supporting a secondary provider configuration
        aws.replica_region,
      ]
    }
  }

  # Backend configuration will be defined at the root module level
  # This ensures state is stored consistently across all environments
  # The backend should support:
  # - State locking to prevent concurrent modifications
  # - Encryption for sensitive data protection
  # - Versioning for state history tracking
}

# Provider configuration will be handled at the environment level
# This allows different environments to use different provider configurations
# while sharing the same module code.
#
# Example provider configuration in the root module:
#
# provider "aws" {
#   region = var.primary_region
#   # Other provider settings like assume_role, etc.
# }
#
# provider "aws" {
#   alias  = "replica_region"
#   region = var.replica_region
#   # Other provider settings like assume_role, etc.
# }