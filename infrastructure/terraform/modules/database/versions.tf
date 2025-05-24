/**
 * Database Module Version Constraints
 *
 * This file defines the Terraform and provider version constraints for the database module,
 * ensuring compatibility and consistent behavior across environments. It supports deployment
 * to AWS, Azure, or GCP depending on the selected cloud provider.
 */

terraform {
  # Require Terraform version 1.5.0 or higher for stability and feature support
  required_version = ">= 1.5.0"

  # Define required providers with version constraints
  required_providers {
    # AWS provider for RDS PostgreSQL deployment
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0, < 6.0.0"
    }

    # Azure provider for Azure Database for PostgreSQL deployment
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.65.0, < 4.0.0"
      configuration_aliases = [azurerm.replica-region]
    }

    # Google provider for Cloud SQL PostgreSQL deployment
    google = {
      source  = "hashicorp/google"
      version = ">= 4.80.0, < 5.0.0"
    }

    # Random provider for generating unique identifiers
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5.0, < 4.0.0"
    }

    # Time provider for creating time-based resources
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9.0, < 1.0.0"
    }
  }
}

# Provider feature blocks for specific cloud providers

# Azure provider features for PostgreSQL management
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    
    key_vault {
      purge_soft_delete_on_destroy = false
      recover_soft_deleted_key_vaults = true
    }
    
    postgresql_server {
      # Enable PostgreSQL-specific features
    }
  }
}

# AWS provider configuration for multi-region support
provider "aws" {
  # Default region configuration is inherited from root module
  # Additional region-specific configurations can be added as needed
}

# Google provider configuration
provider "google" {
  # Default project and region configuration is inherited from root module
}