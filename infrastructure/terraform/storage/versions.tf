/**
 * versions.tf
 *
 * This file defines the Terraform and provider versions required for the storage infrastructure.
 * It ensures consistent deployment across different environments and team members.
 */

terraform {
  # Require Terraform version 1.12.0 or higher as specified in the technical specification
  required_version = ">= 1.12.0"

  # Define required providers with specific version constraints
  required_providers {
    # AWS provider for S3-compatible storage with AES-256 encryption
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0, < 6.0.0"
    }
  }

  # Backend configuration will be defined in environment-specific files
  # This ensures proper state management across different deployment environments
  backend "s3" {}
}

# Provider configuration is defined in environment-specific files
# This ensures proper configuration across different deployment environments