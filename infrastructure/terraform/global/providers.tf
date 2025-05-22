# =============================================================================
# Terraform Provider Configuration for MCA Application Processing System
# =============================================================================
# This file configures the cloud providers (AWS, Azure, GCP) for the MCA
# Application Processing System infrastructure. It establishes the connection
# between Terraform and the cloud environments where resources will be provisioned.
# 
# The configuration supports multi-region deployments for high availability
# as specified in Section 8.2.1 of the technical specification.
# =============================================================================

# Configure Terraform itself
terraform {
  # Specify required Terraform version
  required_version = ">= 1.0.0, < 2.0.0"

  # Configure backend for storing Terraform state
  # Using S3 for AWS deployments with state locking via DynamoDB
  backend "s3" {
    bucket         = "dollarfunding-terraform-state"
    key            = "global/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }

  # Define required providers with version constraints
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0, < 6.0.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0.0, < 5.0.0"
    }
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0.0, < 7.0.0"
    }
  }
}

# =============================================================================
# AWS Provider Configuration
# =============================================================================
# Primary cloud provider for the MCA Application Processing System
# Configured for multi-region deployment with us-east-1 as the primary region
# and us-west-2 as the secondary region for disaster recovery.

provider "aws" {
  region = "us-east-1"
  
  # Default tags applied to all AWS resources
  default_tags {
    tags = {
      Project     = "MCA-Application-System"
      Environment = "global"
      ManagedBy   = "terraform"
    }
  }
}

# Secondary AWS region provider for disaster recovery
provider "aws" {
  alias  = "west"
  region = "us-west-2"
  
  # Default tags applied to all AWS resources in secondary region
  default_tags {
    tags = {
      Project     = "MCA-Application-System"
      Environment = "global"
      ManagedBy   = "terraform"
      Region      = "secondary"
    }
  }
}

# =============================================================================
# Azure Provider Configuration
# =============================================================================
# Secondary cloud provider for specific services and multi-cloud strategy

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy = false
      recover_soft_deleted_key_vaults = true
    }
  }
  
  # Default Azure region
  location = "East US"
  
  # Default tags for Azure resources
  tags = {
    Project     = "MCA-Application-System"
    Environment = "global"
    ManagedBy   = "terraform"
  }
}

# Secondary Azure region provider for disaster recovery
provider "azurerm" {
  alias = "west"
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy = false
      recover_soft_deleted_key_vaults = true
    }
  }
  
  # Secondary Azure region
  location = "West US"
  
  # Default tags for Azure resources in secondary region
  tags = {
    Project     = "MCA-Application-System"
    Environment = "global"
    ManagedBy   = "terraform"
    Region      = "secondary"
  }
}

# =============================================================================
# Google Cloud Provider Configuration
# =============================================================================
# Tertiary cloud provider for specific services and multi-cloud strategy

provider "google" {
  project = "dollarfunding-mca-system"
  region  = "us-east1"
  zone    = "us-east1-b"
}

# Secondary GCP region provider for disaster recovery
provider "google" {
  alias   = "west"
  project = "dollarfunding-mca-system"
  region  = "us-west1"
  zone    = "us-west1-b"
}

# =============================================================================
# Provider Feature Flags and Optimizations
# =============================================================================
# These settings configure provider-specific optimizations and features

# AWS Provider optimizations
provider "aws" {
  alias = "optimized"
  region = "us-east-1"
  
  # Skip metadata API check for faster operations in environments where
  # the metadata API is not available (e.g., local development)
  skip_metadata_api_check = true
  
  # Skip requesting account ID during initialization
  skip_requesting_account_id = true
  
  # Default tags applied to all AWS resources
  default_tags {
    tags = {
      Project     = "MCA-Application-System"
      Environment = "global"
      ManagedBy   = "terraform"
    }
  }
}