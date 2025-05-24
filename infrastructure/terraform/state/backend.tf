# Terraform state backend configuration
# This file configures the remote backend for storing Terraform state files securely
# across environments, ensuring state is preserved, versioned, and accessible to all
# team members and CI/CD pipelines.

terraform {
  backend "s3" {
    # S3-compatible storage bucket for Terraform state
    # The actual bucket name will be set via -backend-config during terraform init
    # Format: mca-terraform-state-{environment}
    # Example: mca-terraform-state-production, mca-terraform-state-staging
    
    # Region where the S3 bucket is located
    region = "us-east-1"
    
    # Enable state file encryption using AES-256
    encrypt = true
    
    # Enable state file versioning to maintain history
    # This allows for state recovery in case of corruption or accidental changes
    versioning = true
    
    # State file key path within the bucket
    # Format: {environment}/{component}/terraform.tfstate
    # Example: production/database/terraform.tfstate
    key = "terraform.tfstate"
    
    # Use DynamoDB for state locking to prevent concurrent modifications
    # The actual table name will be set via -backend-config during terraform init
    # Format: mca-terraform-locks-{environment}
    # dynamodb_table = "mca-terraform-locks"
    
    # Ensure TLS is used for all API operations
    skip_credentials_validation = false
    skip_region_validation      = false
    skip_metadata_api_check     = false
    skip_s3_checksum            = false
  }
}

# Usage instructions:
# This backend configuration is intentionally parameterized and requires additional
# configuration during initialization. Use the following command pattern:
#
# terraform init \
#   -backend-config="bucket=mca-terraform-state-{environment}" \
#   -backend-config="key={environment}/{component}/terraform.tfstate" \
#   -backend-config="dynamodb_table=mca-terraform-locks-{environment}"
#
# Where:
# - {environment} is one of: development, staging, production
# - {component} is the infrastructure component: database, messaging, cache, etc.
#
# Example for production database:
# terraform init \
#   -backend-config="bucket=mca-terraform-state-production" \
#   -backend-config="key=production/database/terraform.tfstate" \
#   -backend-config="dynamodb_table=mca-terraform-locks-production"