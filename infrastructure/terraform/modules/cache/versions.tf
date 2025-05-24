/**
 * # Cache Module - Terraform Version Constraints
 *
 * This file defines the Terraform and provider version constraints for the cache module.
 * It ensures compatibility and consistent behavior across environments when deploying
 * Redis 7.0 as a distributed caching layer.
 */

terraform {
  # Require Terraform version 1.0.0 or higher for stability and feature support
  required_version = ">= 1.0.0"

  # Define required providers for Redis deployment across different cloud platforms
  required_providers {
    # AWS provider for ElastiCache (AWS managed Redis)
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 6.0.0"
    }

    # Azure provider for Azure Cache for Redis
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0, < 5.0.0"
    }

    # Google Cloud provider for Memorystore (GCP managed Redis)
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}

# Provider configuration for AWS (if AWS is the selected cloud provider)
provider "aws" {
  # Provider configuration will be passed from the root module
  # This block ensures the provider is properly initialized
  # Configuration options like region and credentials are defined in the root module
}

# Provider configuration for Azure (if Azure is the selected cloud provider)
provider "azurerm" {
  # Provider configuration will be passed from the root module
  # This block ensures the provider is properly initialized
  features {}
}

# Provider configuration for Google Cloud (if GCP is the selected cloud provider)
provider "google" {
  # Provider configuration will be passed from the root module
  # This block ensures the provider is properly initialized
  # Configuration options like project and region are defined in the root module
}