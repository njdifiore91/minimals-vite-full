# versions.tf for storage module
# Defines Terraform and provider version constraints for the S3-compatible storage module
# This ensures consistent deployment across environments and team members

terraform {
  # Require Terraform version 1.3.0 or higher
  # This ensures compatibility with modern Terraform features including improved
  # provider configuration and S3 bucket resource handling
  required_version = ">= 1.3.0"

  # Define required providers with specific version constraints
  required_providers {
    # AWS provider for S3-compatible storage with AES-256 encryption
    aws = {
      source  = "hashicorp/aws"
      # Use version 4.0.0 or higher for S3 bucket resource compatibility
      # Version 4.0.0 introduced significant changes to S3 bucket resources
      # Pin to major version 4 to prevent unexpected breaking changes from version 5
      version = ">= 4.0.0, < 5.0.0"
    }
  }

  # Experimental features can be enabled here if needed for S3 functionality
  # experiments = []
}