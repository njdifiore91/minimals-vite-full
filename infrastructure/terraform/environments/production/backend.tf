# -------------------------------------------------------
# TERRAFORM BACKEND CONFIGURATION - PRODUCTION ENVIRONMENT
# -------------------------------------------------------
# This file configures the Terraform backend for storing and
# managing the production environment's state. It specifies
# where and how the Terraform state is stored, enabling
# collaboration between team members and maintaining state
# consistency.
#
# The production environment uses stricter access controls
# and longer retention periods for state files compared to
# other environments, as specified in section 8.2.2 of the
# technical specification.
# -------------------------------------------------------

terraform {
  # Use S3 as the backend for storing Terraform state
  # This provides versioning, encryption, and access controls
  backend "s3" {
    # Production-specific S3 bucket for Terraform state
    bucket = "mca-terraform-state-prod"
    
    # State file path within the bucket
    # Format: environments/production/{component}/terraform.tfstate
    key = "environments/production/terraform.tfstate"
    
    # AWS region where the S3 bucket is located
    region = "us-east-1"
    
    # Enable state file encryption using AES-256 for security compliance
    encrypt = true
    
    # Use DynamoDB for state locking to prevent concurrent modifications
    # This is critical for team-based infrastructure development
    dynamodb_table = "mca-terraform-locks-prod"
    
    # Ensure TLS is used for all API operations
    skip_credentials_validation = false
    skip_region_validation      = false
    skip_metadata_api_check     = false
    skip_s3_checksum            = false
  }
}

# Local variables for backend configuration
locals {
  # Environment name for resource naming and tagging
  environment = "production"
  
  # Backend configuration for the production environment
  backend_config = {
    bucket         = "mca-terraform-state-prod"
    key            = "environments/production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "mca-terraform-locks-prod"
  }
  
  # State locking configuration for the production environment
  # These settings align with the state-locking.tf configuration
  lock_config = {
    table_name     = "mca-terraform-locks-prod"
    read_capacity  = 10
    write_capacity = 10
    ttl_enabled    = true
    ttl_attribute  = "LockExpiration"
    ttl_days       = 7  # 7 day TTL for production locks (longer retention for audit purposes)
  }
}

# Output the backend configuration for reference
output "backend_config" {
  value       = local.backend_config
  description = "Backend configuration for the production environment"
  sensitive   = true
}

# Output the lock configuration for reference
output "lock_config" {
  value       = local.lock_config
  description = "Lock configuration for the production environment"
  sensitive   = true
}

# Usage instructions for initializing with this backend
output "init_instructions" {
  value = <<-EOT
    To initialize Terraform with this backend configuration, run:
    
    terraform init \
      -backend-config="bucket=${local.backend_config.bucket}" \
      -backend-config="key=${local.backend_config.key}" \
      -backend-config="region=${local.backend_config.region}" \
      -backend-config="encrypt=${local.backend_config.encrypt}" \
      -backend-config="dynamodb_table=${local.backend_config.dynamodb_table}"
    
    Note: Ensure you have appropriate AWS credentials configured with
    permissions to access the S3 bucket and DynamoDB table.
  EOT
  description = "Instructions for initializing Terraform with this backend configuration"
}