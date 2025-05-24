# -----------------------------------------------------------------------------
# TERRAFORM STATE LOCKING CONFIGURATION
# -----------------------------------------------------------------------------
# This file implements state locking mechanism to prevent concurrent modifications
# to Terraform state, which could lead to corruption or inconsistent infrastructure.
# It configures DynamoDB for distributed locking, ensuring that only one user or
# CI/CD process can modify the infrastructure at a time.
#
# This configuration supports the GitOps workflow mentioned in section 8.2.2 of
# the technical specification and is designed to be consistent across all
# environments (development, staging, production).
# -----------------------------------------------------------------------------

# Provider configuration is expected to be defined in the root module
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }
}

# Create a DynamoDB table for Terraform state locking
resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = var.lock_table_name
  billing_mode   = "PAY_PER_REQUEST"  # On-demand capacity to minimize costs
  hash_key       = "LockID"
  
  attribute {
    name = "LockID"
    type = "S"
  }
  
  # Enable point-in-time recovery for the lock table
  point_in_time_recovery {
    enabled = true
  }
  
  # Add tags for resource identification and management
  tags = {
    Name        = var.lock_table_name
    Environment = "all"
    Purpose     = "terraform-state-locking"
    ManagedBy   = "terraform"
    Project     = "MCA Application Processing System"
  }
  
  # Prevent accidental deletion of the lock table
  lifecycle {
    prevent_destroy = true
  }
}

# Output the DynamoDB table name for reference in other modules
output "dynamodb_table_name" {
  value       = aws_dynamodb_table.terraform_state_lock.name
  description = "The name of the DynamoDB table used for Terraform state locking"
}

# Output the DynamoDB table ARN for reference in IAM policies
output "dynamodb_table_arn" {
  value       = aws_dynamodb_table.terraform_state_lock.arn
  description = "The ARN of the DynamoDB table used for Terraform state locking"
}

# Output whether stale lock cleanup is enabled
output "stale_lock_cleanup_enabled" {
  value       = var.stale_lock_cleanup_enabled
  description = "Whether automatic cleanup of stale locks is enabled"
}

# Configure automatic cleanup for stale locks
resource "aws_cloudwatch_event_rule" "stale_lock_detection" {
  count       = var.stale_lock_cleanup_enabled ? 1 : 0
  name        = "terraform-stale-lock-detection"
  description = "Trigger cleanup of stale Terraform state locks"
  
  # Run every 6 hours
  schedule_expression = "rate(6 hours)"
  
  tags = {
    Name        = "terraform-stale-lock-detection"
    Environment = "all"
    Purpose     = "terraform-state-locking"
    ManagedBy   = "terraform"
    Project     = "MCA Application Processing System"
  }
}

# Lambda function to clean up stale locks
resource "aws_lambda_function" "lock_cleanup" {
  count           = var.stale_lock_cleanup_enabled ? 1 : 0
  function_name    = "terraform-lock-cleanup"
  description      = "Cleans up stale Terraform state locks"
  runtime          = "nodejs16.x"
  handler          = "index.handler"
  timeout          = 30
  memory_size      = 128
  role             = aws_iam_role.lock_cleanup_role[0].arn
  
  # Inline code for the Lambda function
  filename         = "${path.module}/lock_cleanup.zip"
  source_code_hash = filebase64sha256("${path.module}/lock_cleanup.zip")
  
  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.terraform_state_lock.name
      MAX_LOCK_AGE_HOURS = tostring(var.stale_lock_age_hours)
    }
  }
  
  tags = {
    Name        = "terraform-lock-cleanup"
    Environment = "all"
    Purpose     = "terraform-state-locking"
    ManagedBy   = "terraform"
    Project     = "MCA Application Processing System"
  }
}

# IAM role for the lock cleanup Lambda function
resource "aws_iam_role" "lock_cleanup_role" {
  count = var.stale_lock_cleanup_enabled ? 1 : 0
  name = "terraform-lock-cleanup-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "terraform-lock-cleanup-role"
    Environment = "all"
    Purpose     = "terraform-state-locking"
    ManagedBy   = "terraform"
    Project     = "MCA Application Processing System"
  }
}

# IAM policy for the lock cleanup Lambda function
resource "aws_iam_policy" "lock_cleanup_policy" {
  count       = var.stale_lock_cleanup_enabled ? 1 : 0
  name        = "terraform-lock-cleanup-policy"
  description = "Policy for Terraform lock cleanup Lambda function"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:Scan",
          "dynamodb:DeleteItem",
          "dynamodb:GetItem"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.terraform_state_lock.arn
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
  
  tags = {
    Name        = "terraform-lock-cleanup-policy"
    Environment = "all"
    Purpose     = "terraform-state-locking"
    ManagedBy   = "terraform"
    Project     = "MCA Application Processing System"
  }
}

# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "lock_cleanup_attachment" {
  count      = var.stale_lock_cleanup_enabled ? 1 : 0
  role       = aws_iam_role.lock_cleanup_role[0].name
  policy_arn = aws_iam_policy.lock_cleanup_policy[0].arn
}

# CloudWatch event target to trigger the Lambda function
resource "aws_cloudwatch_event_target" "lock_cleanup_target" {
  count     = var.stale_lock_cleanup_enabled ? 1 : 0
  rule      = aws_cloudwatch_event_rule.stale_lock_detection[0].name
  target_id = "terraform-lock-cleanup"
  arn       = aws_lambda_function.lock_cleanup[0].arn
}

# Permission for CloudWatch to invoke the Lambda function
resource "aws_lambda_permission" "allow_cloudwatch" {
  count         = var.stale_lock_cleanup_enabled ? 1 : 0
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lock_cleanup[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.stale_lock_detection[0].arn
}

# Example backend configuration for reference
locals {
  backend_config_example = <<-EOT
    # Example backend configuration using the state locking DynamoDB table
    # Include this in your Terraform configuration files
    
    terraform {
      backend "s3" {
        bucket         = "mca-terraform-state-bucket"
        key            = "path/to/your/terraform.tfstate"
        region         = "us-east-1"  # Change to your region
        encrypt        = true
        dynamodb_table = "${aws_dynamodb_table.terraform_state_lock.name}"
      }
    }
  EOT
}

# Variables for customizing the state locking configuration
variable "lock_table_name" {
  description = "Name of the DynamoDB table used for Terraform state locking"
  type        = string
  default     = "terraform-state-lock"
}

variable "stale_lock_cleanup_enabled" {
  description = "Whether to enable automatic cleanup of stale locks"
  type        = bool
  default     = true
}

variable "stale_lock_age_hours" {
  description = "Age in hours after which a lock is considered stale"
  type        = number
  default     = 24
}

# Documentation on state locking behavior
locals {
  state_locking_docs = <<-EOT
    # Terraform State Locking
    
    This configuration implements state locking using DynamoDB to prevent concurrent
    modifications to Terraform state files. State locking is critical in environments
    where multiple users or CI/CD processes might attempt to modify infrastructure
    simultaneously.
    
    ## How State Locking Works
    
    1. When a Terraform operation that could modify state begins (apply, destroy),
       Terraform attempts to acquire a lock by writing to the DynamoDB table.
    
    2. If the lock is successfully acquired, the operation proceeds.
    
    3. If another process already holds the lock, Terraform will wait and retry
       for up to 10 minutes (configurable) before failing.
    
    4. Once the operation completes, Terraform automatically releases the lock.
    
    ## Lock Cleanup
    
    A CloudWatch scheduled event triggers a Lambda function every 6 hours to
    clean up stale locks (locks older than 24 hours). This prevents orphaned
    locks from blocking infrastructure operations indefinitely.
    
    ## Environment-Specific Considerations
    
    The state locking mechanism is consistent across all environments (development,
    staging, production) to ensure reliable operation of the GitOps workflow and
    CI/CD pipeline integration.
  EOT
}