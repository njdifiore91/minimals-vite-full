# -------------------------------------------------------
# TERRAFORM WORKSPACE CONFIGURATION
# -------------------------------------------------------
# This file defines workspace configurations for managing
# separate state files for different environments
# (development, staging, production).
#
# The workspace configuration supports the GitOps-based workflow
# described in section 8.2.2 of the technical specification,
# enabling isolated infrastructure management while maintaining
# consistent module structure across environments.
#
# USAGE:
# 1. Create a workspace: terraform workspace new <environment>
#    Valid environments: development, staging, production
#
# 2. Select a workspace: terraform workspace select <environment>
#
# 3. View current workspace: terraform workspace show
#
# 4. List all workspaces: terraform workspace list
#
# Each workspace maintains its own state file in a separate path
# within the configured backend storage, ensuring complete isolation
# between environments while using the same Terraform code.
# -------------------------------------------------------

# Local variables for workspace configuration
locals {
  # Valid workspace names aligned with the environment promotion flow
  # from section 8.2.2 of the technical specification
  valid_workspace_names = [
    "development", # Development environment for feature development
    "staging",     # Pre-production environment for testing
    "production"   # Production environment for live workloads
  ]

  # Ensure current workspace is valid
  is_valid_workspace = contains(local.valid_workspace_names, terraform.workspace)
  
  # Workspace validation message
  workspace_error_message = "Error: Workspace '${terraform.workspace}' is not valid. Must be one of: ${join(", ", local.valid_workspace_names)}"

  # Workspace-specific state paths
  state_path = {
    development = "environments/development"
    staging     = "environments/staging"
    production  = "environments/production"
  }

  # Workspace-specific backend configurations
  backend_config = {
    development = {
      bucket         = "mca-terraform-state-dev"
      key            = "${local.state_path[terraform.workspace]}/terraform.tfstate"
      region         = "us-east-1"
      encrypt        = true
      dynamodb_table = "mca-terraform-locks-dev"
    }
    staging = {
      bucket         = "mca-terraform-state-staging"
      key            = "${local.state_path[terraform.workspace]}/terraform.tfstate"
      region         = "us-east-1"
      encrypt        = true
      dynamodb_table = "mca-terraform-locks-staging"
    }
    production = {
      bucket         = "mca-terraform-state-prod"
      key            = "${local.state_path[terraform.workspace]}/terraform.tfstate"
      region         = "us-east-1"
      encrypt        = true
      dynamodb_table = "mca-terraform-locks-prod"
    }
  }

  # Environment-specific resource configurations based on section 8.8.2 of the technical specification
  # These configurations align with the multi-environment cost considerations
  environment_config = {
    development = {
      # Development environment has minimal viable resources
      kubernetes_node_count = 2
      kubernetes_node_type  = "t3.medium"  # Smallest viable instance size
      db_instance_type      = "db.t3.medium"
      db_replica_count      = 0            # No replicas for development
      redis_node_type       = "cache.t3.small"
      redis_replica_count   = 0            # No replicas for development
      rabbitmq_instance_type = "mq.t3.micro"
      rabbitmq_node_count   = 1            # Single node for development
      s3_lifecycle_rules    = {
        transition_days = 30
        expiration_days = 90
      }
      # Auto-shutdown for cost savings as specified in section 8.8.2
      auto_shutdown = true
      auto_shutdown_hours = "nights-and-weekends" # 7PM-7AM weekdays, all weekend
      # Resource quotas to prevent overconsumption
      resource_quotas = {
        cpu_limit     = "8"
        memory_limit  = "16Gi"
        storage_limit = "100Gi"
      }
      # Use spot instances for non-critical workloads
      use_spot_instances = true
    }
    
    staging = {
      # Staging environment has moderate resources (50% of production)
      # as recommended in section 8.8.2
      kubernetes_node_count = 3
      kubernetes_node_type  = "t3.large"
      db_instance_type      = "db.t3.large"
      db_replica_count      = 1            # Single replica for staging
      redis_node_type       = "cache.t3.medium"
      redis_replica_count   = 1            # Single replica for staging
      rabbitmq_instance_type = "mq.t3.small"
      rabbitmq_node_count   = 3            # 3-node cluster for staging
      s3_lifecycle_rules    = {
        transition_days = 60
        expiration_days = 180
      }
      # No auto-shutdown for staging
      auto_shutdown = false
      auto_shutdown_hours = null
      # Resource quotas for staging
      resource_quotas = {
        cpu_limit     = "16"
        memory_limit  = "32Gi"
        storage_limit = "250Gi"
      }
      # Use spot instances for some workloads
      use_spot_instances = true
    }
    
    production = {
      # Production environment has full resources with redundancy
      # as specified in section 8.8.2
      kubernetes_node_count = 5
      kubernetes_node_type  = "m5.large"
      db_instance_type      = "db.m5.large"
      db_replica_count      = 2            # Two read replicas for production
      redis_node_type       = "cache.m5.large"
      redis_replica_count   = 2            # Two replicas for production
      rabbitmq_instance_type = "mq.m5.large"
      rabbitmq_node_count   = 3            # 3-node cluster for production
      s3_lifecycle_rules    = {
        transition_days = 90
        expiration_days = 365
      }
      # No auto-shutdown for production
      auto_shutdown = false
      auto_shutdown_hours = null
      # Resource quotas for production
      resource_quotas = {
        cpu_limit     = "32"
        memory_limit  = "64Gi"
        storage_limit = "500Gi"
      }
      # Use reserved instances for baseline capacity
      use_spot_instances = false
      reserved_instance_term = "1-year"
    }
  }

  # Current environment configuration based on workspace
  current_environment = local.is_valid_workspace ? local.environment_config[terraform.workspace] : null
  current_backend     = local.is_valid_workspace ? local.backend_config[terraform.workspace] : null
}

# Validate workspace name to ensure it matches one of the defined environments
# This prevents accidental creation of environments outside the promotion flow
resource "null_resource" "workspace_validator" {
  count = local.is_valid_workspace ? 0 : 1
  
  # Fail the Terraform run if an invalid workspace is detected
  provisioner "local-exec" {
    command = "echo '${local.workspace_error_message}' && exit 1"
  }

  # This lifecycle block ensures the validation runs on every apply
  lifecycle {
    create_before_destroy = true
  }
}

# Output current workspace information
output "current_workspace" {
  value = terraform.workspace
  description = "The current Terraform workspace"
}

output "environment_config" {
  value = local.current_environment
  description = "Configuration for the current environment"
  sensitive = true
}

# Workspace-specific tags to be applied to all resources
# These tags support the cost allocation and monitoring requirements
# specified in section 8.8.3 of the technical specification
locals {
  # Common tags applied to all resources across all environments
  common_tags = {
    Environment     = terraform.workspace
    ManagedBy       = "Terraform"
    Project         = "MCA-Application"
    GitOpsWorkflow  = "true"
    Application     = "MerchantCashAdvance"
    Owner           = "DollarFunding-DevOps"
  }
  
  # Additional environment-specific tags for cost allocation and governance
  environment_tags = {
    development = {
      CostCenter     = "Development"
      AutoShutdown   = "true"
      DataSensitivity = "low"
      BudgetCategory = "Development"
      BudgetAlert    = "70,85,95"
      ResourceTier   = "minimal"
    }
    staging = {
      CostCenter     = "PreProduction"
      AutoShutdown   = "false"
      DataSensitivity = "medium"
      BudgetCategory = "PreProduction"
      BudgetAlert    = "70,85,95"
      ResourceTier   = "standard"
      BackupSchedule = "daily"
      BackupRetention = "30-days"
    }
    production = {
      CostCenter     = "Production"
      AutoShutdown   = "false"
      DataSensitivity = "high"
      BudgetCategory = "Production"
      BudgetAlert    = "70,85,95"
      ResourceTier   = "premium"
      BackupSchedule = "daily"
      BackupRetention = "7-years"
      ComplianceLevel = "high"
      SLA            = "99.9"
    }
  }
  
  # Combined tags for the current environment
  current_tags = local.is_valid_workspace ? merge(local.common_tags, local.environment_tags[terraform.workspace]) : local.common_tags
}

# Export tags for use in other modules
output "resource_tags" {
  value = local.current_tags
  description = "Tags to be applied to resources in the current environment"
}

# Workspace-specific backend configuration
# This is used by the backend.tf file to configure the appropriate
# state storage location based on the current workspace
output "backend_config" {
  value = local.current_backend
  description = "Backend configuration for the current workspace"
}

# Workspace-specific state path
# This is used to determine where state files should be stored
# for each environment
output "state_path" {
  value = local.is_valid_workspace ? local.state_path[terraform.workspace] : null
  description = "State path for the current workspace"
}

# Terraform workspace initialization helper
# This resource provides guidance on how to create and switch workspaces
resource "null_resource" "workspace_helper" {
  # Only create this resource when explicitly requested
  count = terraform.workspace == "default" ? 1 : 0
  
  provisioner "local-exec" {
    command = <<-EOT
      echo "\nCurrent workspace: ${terraform.workspace}\n"
      echo "To create a new workspace, run:"
      echo "  terraform workspace new <workspace_name>"
      echo "\nTo switch to an existing workspace, run:"
      echo "  terraform workspace select <workspace_name>"
      echo "\nValid workspaces are: ${join(", ", local.valid_workspace_names)}"
      echo "\nNote: You are currently in the 'default' workspace, which is not a valid environment workspace."
      echo "Please create or select one of the valid workspaces before applying changes.\n"
    EOT
  }
}