# Backend configuration for the MCA Application Processing System - Production Environment
#
# This file configures the Terraform backend for storing and managing the production environment's state.
# It enables team collaboration by providing a centralized, versioned state storage with locking
# to prevent concurrent modifications by multiple team members.
# Production environment has stricter access controls and enhanced security measures.

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
    key            = "mca/production/terraform.tfstate"  # Path within the bucket for production environment
    region         = "us-east-1"                      # Primary region for state storage
    encrypt        = true                             # Encrypt state file at rest
    dynamodb_table = "terraform-locks"               # DynamoDB table for state locking
    
    # Production-specific backend settings with enhanced security
    # role_arn       = "arn:aws:iam::ACCOUNT_ID:role/TerraformProductionRole"  # Production-specific IAM role
    # kms_key_id     = "arn:aws:kms:us-east-1:ACCOUNT_ID:key/terraform-state-key"  # KMS key for additional encryption
    
    # State file versioning is enabled at the bucket level
    # This allows for state recovery in case of accidental corruption
    
    # Workspace support - if using Terraform workspaces, the state path will include the workspace name
    # For example, with workspace 'feature-x', the state would be at mca/production/feature-x/terraform.tfstate
  }
  
  # Experimental features can be enabled here if needed
  # experiments = [example]
}