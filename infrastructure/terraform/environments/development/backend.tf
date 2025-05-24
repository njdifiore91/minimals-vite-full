# Backend configuration for the MCA Application Processing System - Development Environment
#
# This file configures the Terraform backend for storing and managing the development environment's state.
# It enables team collaboration by providing a centralized, versioned state storage with locking
# to prevent concurrent modifications by multiple team members.
# The development environment uses a simplified configuration while maintaining core functionality.

terraform {
  # Terraform version constraint - ensures compatibility with the codebase
  required_version = ">= 1.0.0"

  # Required providers with version constraints
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }

  # Backend configuration for state storage
  # The S3 backend stores the Terraform state remotely, allowing for team collaboration
  # and providing state versioning, encryption, and locking capabilities
  backend "s3" {
    bucket         = "dollarfunding-terraform-state"  # Central bucket for all terraform states
    key            = "mca/development/terraform.tfstate"  # Path within the bucket for development environment
    region         = "us-east-1"                      # Primary region for state storage
    encrypt        = true                             # Encrypt state file at rest
    dynamodb_table = "terraform-locks"               # DynamoDB table for state locking
    
    # Development-specific backend settings
    # These would typically be provided via CLI or environment variables
    # profile        = "development"                  # AWS profile for development environment
    
    # State file versioning is enabled at the bucket level
    # This allows for state recovery in case of accidental corruption
    
    # Workspace support - if using Terraform workspaces, the state path will include the workspace name
    # For example, with workspace 'feature-x', the state would be at mca/development/feature-x/terraform.tfstate
    # This is particularly useful in development for feature branches and developer-specific changes
  }
  
  # Experimental features can be enabled here if needed
  # experiments = [example]
}