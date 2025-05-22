# Backend configuration for the MCA Application Processing System - Production Environment

terraform {
  # Terraform version constraint
  required_version = ">= 1.0.0"

  # Required providers
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }

  # Backend configuration for state storage
  backend "s3" {
    bucket         = "dollarfunding-terraform-state"
    key            = "mca/production/terraform.tfstate"
    region         = "us-east-1"  # Primary region for state storage
    encrypt        = true         # Encrypt state file
    dynamodb_table = "terraform-locks"  # DynamoDB table for state locking
    
    # Additional backend settings
    # These would typically be provided via CLI or environment variables
    # profile        = "production"
    # role_arn       = "arn:aws:iam::ACCOUNT_ID:role/TerraformExecutionRole"
  }
}