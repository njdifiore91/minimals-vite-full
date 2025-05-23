# -------------------------------------------------------
# TERRAFORM WORKSPACE CONFIGURATION
# -------------------------------------------------------
# This file defines Terraform workspace configurations for
# managing separate state files for different environments
# (development, staging, production).
#
# Workspaces enable isolated infrastructure management while
# maintaining consistent module structure across environments.
# This supports the GitOps-based workflow described in
# section 8.2.2 of the technical specification.
#
# The configuration aligns with the environment promotion flow
# (development -> staging -> production) and ensures that
# environment-specific configurations are properly isolated.
#
# This workspace configuration is a critical component of the
# infrastructure validation and deployment process in the
# GitOps workflow, where infrastructure changes are validated
# through Terraform plan execution before being applied to
# each environment.
# -------------------------------------------------------

# Define valid workspaces that correspond to our environments
locals {
  # List of valid workspace names
  valid_workspaces = ["development", "staging", "production"]
  
  # Check if current workspace is valid
  is_valid_workspace = contains(local.valid_workspaces, terraform.workspace)
  
  # Mapping of workspace names to environment names (for consistency)
  workspace_to_environment = {
    development = "development"
    staging     = "staging"
    production  = "production"
  }
  
  # Current environment based on workspace
  current_environment = local.is_valid_workspace ? local.workspace_to_environment[terraform.workspace] : "unknown"
  
  # Environment-specific state file paths
  state_file_paths = {
    development = "env/development/terraform.tfstate"
    staging     = "env/staging/terraform.tfstate"
    production  = "env/production/terraform.tfstate"
  }
  
  # Current state file path based on workspace
  current_state_path = local.is_valid_workspace ? local.state_file_paths[terraform.workspace] : "unknown"
  
  # Standard tags to apply to all resources based on workspace
  current_tags = {
    Environment = local.current_environment
    ManagedBy   = "Terraform"
    Workspace   = terraform.workspace
    Project     = "MCA Application Processing System"
  }
  
  # Environment-specific configuration defaults based on section 8.4 of the technical specification
  environment_config = {
    development = {
      # Region configuration
      region                 = "us-east-1"
      multi_az               = true
      
      # Compute resources
      instance_type          = "t3.medium"
      auto_scaling_min       = 1
      auto_scaling_max       = 3
      
      # Database configuration (PostgreSQL 14)
      db_instance_class      = "db.t3.medium"
      db_replica_count       = 1  # 1 read replica for development
      db_multi_az            = true
      db_backup_retention    = 7  # 7 days backup retention
      db_storage_type        = "gp2"
      db_iops                = 1000
      db_connection_timeout  = 30
      
      # Redis configuration (Redis 7.0)
      redis_node_type        = "cache.t3.medium"
      redis_num_shards       = 1
      redis_replicas_per_shard = 1
      redis_data_tiering     = false
      
      # Monitoring configuration
      enable_detailed_monitoring = true
      log_retention_days     = 7
      metrics_interval       = 15  # 15-second metrics interval
      
      # S3 storage configuration
      s3_storage_class       = "STANDARD"
      s3_versioning          = true
      s3_lifecycle_days      = 30
    },
    staging = {
      # Region configuration
      region                 = "us-east-1"
      multi_az               = true
      
      # Compute resources
      instance_type          = "t3.large"
      auto_scaling_min       = 2
      auto_scaling_max       = 4
      
      # Database configuration (PostgreSQL 14)
      db_instance_class      = "db.t3.large"
      db_replica_count       = 1  # 1 read replica for staging
      db_multi_az            = true
      db_backup_retention    = 14  # 14 days backup retention
      db_storage_type        = "gp2"
      db_iops                = 1000
      db_connection_timeout  = 30
      
      # Redis configuration (Redis 7.0)
      redis_node_type        = "cache.t3.large"
      redis_num_shards       = 2
      redis_replicas_per_shard = 1
      redis_data_tiering     = false
      
      # Monitoring configuration
      enable_detailed_monitoring = true
      log_retention_days     = 14
      metrics_interval       = 15  # 15-second metrics interval
      
      # S3 storage configuration
      s3_storage_class       = "STANDARD"
      s3_versioning          = true
      s3_lifecycle_days      = 90
    },
    production = {
      # Region configuration
      region                 = "us-east-1"
      multi_az               = true
      
      # Compute resources
      instance_type          = "m5.large"
      auto_scaling_min       = 3
      auto_scaling_max       = 6
      
      # Database configuration (PostgreSQL 14)
      db_instance_class      = "db.m5.large"
      db_replica_count       = 2  # 2 read replicas for production as specified in 8.4.3
      db_multi_az            = true
      db_backup_retention    = 30  # 30 days backup retention
      db_storage_type        = "gp2"
      db_iops                = 1000
      db_connection_timeout  = 30
      
      # Redis configuration (Redis 7.0)
      redis_node_type        = "cache.m5.large"
      redis_num_shards       = 3  # Cluster mode with 3+ shards as specified in 8.4.5
      redis_replicas_per_shard = 1  # At least 1 replica per shard
      redis_data_tiering     = true  # Memory tiering with SSD persistence
      
      # Monitoring configuration
      enable_detailed_monitoring = true
      log_retention_days     = 30
      metrics_interval       = 10  # 10-second metrics interval
      
      # S3 storage configuration
      s3_storage_class       = "STANDARD"
      s3_versioning          = true
      s3_lifecycle_days      = 365  # 1 year lifecycle for production
    }
  }
  
  # Current environment configuration based on workspace
  current_config = local.is_valid_workspace ? local.environment_config[terraform.workspace] : null
}

# Backend configuration for S3 state storage
# This is a partial configuration that will be completed
# by environment-specific backend configurations
terraform {
  backend "s3" {
    # Common backend configuration
    encrypt        = true
    # The bucket name will be provided in the backend configuration
    # The key will be determined by the workspace
    # The region will be provided in the backend configuration
    # The dynamodb_table will be provided by the state-locking.tf configuration
  }
}

# S3 backend configuration details
# These are used in the CI/CD pipeline to generate the backend configuration
locals {
  # S3 bucket names for state storage
  state_bucket_names = {
    development = "mca-terraform-state-dev"
    staging     = "mca-terraform-state-staging"
    production  = "mca-terraform-state-prod"
  }
  
  # Current state bucket name based on workspace
  current_state_bucket = local.is_valid_workspace ? local.state_bucket_names[terraform.workspace] : null
  
  # State file key patterns
  # These follow the GitOps workflow pattern described in section 8.2.2
  state_key_patterns = {
    development = "env/development/%s/terraform.tfstate"
    staging     = "env/staging/%s/terraform.tfstate"
    production  = "env/production/%s/terraform.tfstate"
  }
  
  # DynamoDB table names for state locking (from state-locking.tf)
  # This ensures consistency with the state locking configuration
  lock_table_names = {
    development = "mca-terraform-locks-dev"
    staging     = "mca-terraform-locks-staging"
    production  = "mca-terraform-locks-prod"
  }
  
  # Current lock table name based on workspace
  current_lock_table = local.is_valid_workspace ? local.lock_table_names[terraform.workspace] : null
}

# Workspace validation resource
# This resource will fail if an invalid workspace is used
resource "null_resource" "workspace_validator" {
  # Only create this resource when the workspace is invalid
  count = local.is_valid_workspace ? 0 : 1
  
  provisioner "local-exec" {
    command = <<-EOT
      echo "\nERROR: Invalid Terraform workspace: '${terraform.workspace}'\n"
      echo "Valid workspaces are: ${join(", ", local.valid_workspaces)}"
      echo "\nTo create and switch to a valid workspace, use:"
      echo "  terraform workspace new <workspace_name>"
      echo "  terraform workspace select <workspace_name>"
      echo "\nCurrent workspaces:"
      terraform workspace list
      exit 1
    EOT
  }
}

# Helper resource for workspace management
resource "null_resource" "workspace_helper" {
  # Only create this resource when explicitly requested
  count = terraform.workspace == "default" ? 1 : 0
  
  provisioner "local-exec" {
    command = <<-EOT
      echo "\nWorkspace Management Information:\n"
      echo "Current workspace: ${terraform.workspace}"
      echo "\nAvailable workspaces:"
      terraform workspace list
      echo "\nTo create a new workspace:"
      echo "  terraform workspace new <workspace_name>"
      echo "\nTo switch workspaces:"
      echo "  terraform workspace select <workspace_name>"
      echo "\nValid workspaces for this project:"
      echo "  ${join(", ", local.valid_workspaces)}"
      echo "\nEnvironment Promotion Flow (GitOps Workflow):"
      echo "  development -> staging -> production"
      echo "\nWorkspace Usage in CI/CD Pipeline:"
      echo "  1. Terraform init with workspace-specific backend config"
      echo "  2. Terraform workspace select <environment>"
      echo "  3. Terraform plan for infrastructure validation"
      echo "  4. Terraform apply for infrastructure provisioning"
      echo "  5. Helm deploy to the appropriate Kubernetes namespace"
      echo "\nPlease select a valid workspace before proceeding."
    EOT
  }
}

# Output current workspace information
output "current_workspace" {
  value       = terraform.workspace
  description = "The current Terraform workspace"
}

# Output current environment
output "current_environment" {
  value       = local.current_environment
  description = "The current environment based on the Terraform workspace"
}

# Output current state file path
output "current_state_path" {
  value       = local.current_state_path
  description = "The path to the current Terraform state file"
}

# Output workspace validation status
output "workspace_validation" {
  value       = local.is_valid_workspace ? "Valid workspace: ${terraform.workspace}" : "Invalid workspace: ${terraform.workspace}"
  description = "Validation status of the current workspace"
}

# Output environment-specific configuration
output "environment_config" {
  value       = local.current_config
  description = "Environment-specific configuration based on the current workspace"
  sensitive   = true  # Mark as sensitive to avoid exposing in logs
}

# Output S3 backend configuration for use in CI/CD pipelines
output "backend_config" {
  value = {
    bucket         = local.current_state_bucket
    key_pattern    = local.is_valid_workspace ? local.state_key_patterns[terraform.workspace] : null
    region         = local.is_valid_workspace ? local.current_config.region : null
    dynamodb_table = local.current_lock_table
    encrypt        = true
  }
  description = "S3 backend configuration for the current workspace"
}

# Output Kubernetes namespace for the current environment
output "kubernetes_namespace" {
  value       = "mca-${local.current_environment}"
  description = "Kubernetes namespace for the current environment"
}

# Output resource naming prefix for the current environment
output "resource_prefix" {
  value       = "mca-${local.current_environment}"
  description = "Resource naming prefix for the current environment"
}