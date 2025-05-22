# -------------------------------------------------------
# TERRAFORM STATE LOCKING CONFIGURATION
# -------------------------------------------------------
# This file implements state locking using DynamoDB to prevent
# concurrent modifications to Terraform state, which could lead
# to corruption or inconsistent infrastructure.
#
# State locking is critical for the GitOps workflow described
# in section 8.2.2 of the technical specification, ensuring
# that only one user or CI/CD process can modify the
# infrastructure at a time.
#
# The configuration supports automatic lock cleanup for failed
# operations and implements consistent locking across all
# environments (development, staging, production).
# -------------------------------------------------------

# Local variables for state locking configuration
locals {
  # Default lock timeout in seconds (15 minutes)
  # This prevents permanent lock-outs in case of failed operations
  default_lock_timeout = 900
  
  # Environment-specific lock configurations
  lock_config = {
    development = {
      table_name     = "mca-terraform-locks-dev"
      read_capacity  = 5
      write_capacity = 5
      ttl_enabled    = true
      ttl_attribute  = "LockExpiration"
      ttl_days       = 1  # 1 day TTL for development locks
    },
    staging = {
      table_name     = "mca-terraform-locks-staging"
      read_capacity  = 5
      write_capacity = 5
      ttl_enabled    = true
      ttl_attribute  = "LockExpiration"
      ttl_days       = 2  # 2 day TTL for staging locks
    },
    production = {
      table_name     = "mca-terraform-locks-prod"
      read_capacity  = 10
      write_capacity = 10
      ttl_enabled    = true
      ttl_attribute  = "LockExpiration"
      ttl_days       = 7  # 7 day TTL for production locks (longer retention for audit purposes)
    }
  }
  
  # Current environment lock configuration based on workspace
  current_lock_config = local.is_valid_workspace ? local.lock_config[terraform.workspace] : null
}

# DynamoDB table for Terraform state locking
# This table is used to prevent concurrent modifications to the Terraform state
# by creating a distributed locking mechanism
resource "aws_dynamodb_table" "terraform_state_lock" {
  # Only create the table if we're in a valid workspace
  count = local.is_valid_workspace ? 1 : 0
  
  # Use the environment-specific table name from lock_config
  name = local.current_lock_config.table_name
  
  # The hash key must be LockID for Terraform state locking
  # This is a requirement for Terraform to use the table for locking
  hash_key = "LockID"
  
  # Use PAY_PER_REQUEST billing mode for cost optimization
  # This is more cost-effective than provisioned capacity for state locking
  # which typically has sporadic, low-volume usage patterns
  billing_mode = "PAY_PER_REQUEST"
  
  # Define the LockID attribute (required for Terraform state locking)
  attribute {
    name = "LockID"
    type = "S"  # String type
  }
  
  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }
  
  # Enable TTL for automatic lock cleanup of failed operations
  # This ensures that locks are automatically released after a specified time
  # even if the Terraform operation fails unexpectedly
  dynamic "ttl" {
    for_each = local.current_lock_config.ttl_enabled ? [1] : []
    content {
      enabled        = true
      attribute_name = local.current_lock_config.ttl_attribute
    }
  }
  
  # Apply standard resource tags plus lock-specific tags
  tags = merge(local.current_tags, {
    Name        = "Terraform State Lock Table"
    Description = "DynamoDB table for Terraform state locking"
    Service     = "Terraform"
    Component   = "State Management"
  })
  
  # Prevent destruction of the lock table to avoid disrupting operations
  lifecycle {
    prevent_destroy = true
  }
}

# IAM policy document for state locking
# This policy grants the necessary permissions for Terraform to use
# the DynamoDB table for state locking
data "aws_iam_policy_document" "terraform_state_lock" {
  count = local.is_valid_workspace ? 1 : 0
  
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem"
    ]
    
    resources = [
      aws_dynamodb_table.terraform_state_lock[0].arn
    ]
    
    effect = "Allow"
  }
}

# Output the DynamoDB table name for use in backend configuration
output "dynamodb_lock_table_name" {
  value       = local.is_valid_workspace ? aws_dynamodb_table.terraform_state_lock[0].name : null
  description = "The name of the DynamoDB table used for Terraform state locking"
}

# Output the DynamoDB table ARN for IAM policy configuration
output "dynamodb_lock_table_arn" {
  value       = local.is_valid_workspace ? aws_dynamodb_table.terraform_state_lock[0].arn : null
  description = "The ARN of the DynamoDB table used for Terraform state locking"
}

# Helper resource to provide guidance on state locking
resource "null_resource" "state_lock_helper" {
  # Only create this resource when explicitly requested
  count = terraform.workspace == "default" ? 1 : 0
  
  provisioner "local-exec" {
    command = <<-EOT
      echo "\nState Locking Information:\n"
      echo "Terraform uses state locking to prevent concurrent operations on the same state."
      echo "If a state becomes locked and the process that locked it has terminated, you can use:"
      echo "  terraform force-unlock <LOCK_ID>"
      echo "\nTo disable state locking temporarily (not recommended):"
      echo "  terraform apply -lock=false"
      echo "\nTo set a custom lock timeout:"
      echo "  terraform apply -lock-timeout=<DURATION>"
      echo "  Example: terraform apply -lock-timeout=10m (10 minutes)"
    EOT
  }
}