/**
 * # PostgreSQL Database Backup and Disaster Recovery Module
 *
 * This Terraform configuration manages comprehensive backup, point-in-time recovery, and disaster recovery
 * configurations for PostgreSQL databases in the MCA Application Processing System. It implements automated
 * daily backups with 30-day retention, snapshot scheduling, and cross-region replication for disaster recovery.
 *
 * ## Features
 *
 * - Automated daily backups with 30-day retention
 * - Point-in-time recovery with 5-minute RPO
 * - Cross-region replication for disaster recovery (RPO: 15min, RTO: 30min)
 * - Snapshot scheduling and lifecycle policies
 * - Backup encryption and security
 * - Database archival process with 7-year retention period
 *
 * ## Usage
 *
 * ```hcl
 * module "postgres_database" {
 *   source = "./modules/database"
 *
 *   environment = "production"
 *   enable_cross_region_backup = true
 *   backup_retention_period = 30
 *   enable_long_term_retention = true
 *   long_term_retention_period = 2555 # 7 years in days
 * }
 * ```
 */

# ------------------------------------------------------------------------------
# LOCAL VARIABLES
# ------------------------------------------------------------------------------

locals {
  # Backup settings based on environment
  backup_retention_days = var.backup_retention_period > 0 ? var.backup_retention_period : 30
  
  # Long-term retention settings (7 years = 2555 days)
  long_term_retention_days = var.long_term_retention_period > 0 ? var.long_term_retention_period : 2555
  
  # Snapshot settings
  snapshot_frequency = local.is_production ? "daily" : (local.is_staging ? "daily" : "weekly")
  
  # Cross-region backup settings
  enable_cross_region = var.enable_cross_region_backup && (local.is_production || local.is_staging)
  destination_region = var.backup_destination_region != "" ? var.backup_destination_region : "us-west-2" # Default fallback region
  
  # Backup tagging
  backup_tags = merge(local.default_tags, var.tags, {
    BackupType = "Automated"
    RetentionPeriod = local.backup_retention_days
  })
}

# ------------------------------------------------------------------------------
# DATA SOURCES
# ------------------------------------------------------------------------------

# Get the current AWS region
data "aws_region" "current" {}

# Get the current AWS account ID
data "aws_caller_identity" "current" {}

# ------------------------------------------------------------------------------
# CROSS-REGION BACKUP REPLICATION
# ------------------------------------------------------------------------------

# Configure cross-region automated backup replication for disaster recovery
resource "aws_db_instance_automated_backups_replication" "cross_region_backup" {
  count = local.enable_cross_region ? 1 : 0
  
  source_db_instance_arn = aws_db_instance.postgres_primary.arn
  retention_period       = local.backup_retention_days
  kms_key_id             = var.enable_encryption ? var.cross_region_kms_key_id : null
  
  # Specify the destination region for backup replication
  provider = aws.backup_region
  
  # Add lifecycle policy to prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }
  
  depends_on = [
    aws_db_instance.postgres_primary
  ]
}

# ------------------------------------------------------------------------------
# AWS BACKUP PLAN FOR LONG-TERM RETENTION
# ------------------------------------------------------------------------------

# Create an AWS Backup vault for long-term database backups
resource "aws_backup_vault" "long_term_vault" {
  count = var.enable_long_term_retention ? 1 : 0
  
  name        = "${local.db_identifier}-long-term-vault"
  kms_key_arn = var.enable_encryption ? var.kms_key_id : null
  
  tags = merge(local.backup_tags, {
    RetentionPeriod = local.long_term_retention_days
    Purpose         = "LongTermRetention"
  })
}

# Create an AWS Backup plan for long-term retention (7 years)
resource "aws_backup_plan" "long_term_plan" {
  count = var.enable_long_term_retention ? 1 : 0
  
  name = "${local.db_identifier}-long-term-plan"
  
  rule {
    rule_name         = "${local.db_identifier}-monthly-rule"
    target_vault_name = aws_backup_vault.long_term_vault[0].name
    schedule          = "cron(0 0 1 * ? *)"
    
    # Monthly backups retained for 7 years (2555 days)
    lifecycle {
      delete_after = local.long_term_retention_days
    }
    
    # Enable continuous backup for point-in-time recovery
    enable_continuous_backup = true
    
    # Copy actions for cross-region redundancy of long-term backups
    dynamic "copy_action" {
      for_each = local.enable_cross_region ? [1] : []
      
      content {
        destination_vault_arn = "arn:aws:backup:${local.destination_region}:${data.aws_caller_identity.current.account_id}:backup-vault:${aws_backup_vault.long_term_vault[0].name}"
        
        lifecycle {
          delete_after = local.long_term_retention_days
        }
      }
    }
  }
  
  # Add quarterly backup rule for critical regulatory compliance
  rule {
    rule_name         = "${local.db_identifier}-quarterly-rule"
    target_vault_name = aws_backup_vault.long_term_vault[0].name
    schedule          = "cron(0 0 1 1,4,7,10 ? *)"
    
    # Quarterly backups retained for 7 years (2555 days)
    lifecycle {
      delete_after = local.long_term_retention_days
      cold_storage_after = 90 # Move to cold storage after 90 days
    }
  }
  
  tags = merge(local.backup_tags, {
    Purpose = "LongTermRetention"
  })
  
  depends_on = [
    aws_backup_vault.long_term_vault
  ]
}

# Select the RDS database as a resource for the backup plan
resource "aws_backup_selection" "db_backup_selection" {
  count = var.enable_long_term_retention ? 1 : 0
  
  name         = "${local.db_identifier}-selection"
  iam_role_arn = aws_iam_role.backup_role[0].arn
  plan_id      = aws_backup_plan.long_term_plan[0].id
  
  resources = [
    aws_db_instance.postgres_primary.arn
  ]
  
  depends_on = [
    aws_backup_plan.long_term_plan,
    aws_iam_role.backup_role
  ]
}

# ------------------------------------------------------------------------------
# IAM ROLE FOR AWS BACKUP
# ------------------------------------------------------------------------------

# Create an IAM role for AWS Backup to perform database backups
resource "aws_iam_role" "backup_role" {
  count = var.enable_long_term_retention ? 1 : 0
  
  name               = "${local.db_identifier}-backup-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.backup_tags
}

# Attach the AWS Backup service role policy to the backup role
resource "aws_iam_role_policy_attachment" "backup_policy_attachment" {
  count = var.enable_long_term_retention ? 1 : 0
  
  role       = aws_iam_role.backup_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

# Attach additional policy for RDS restore operations
resource "aws_iam_role_policy_attachment" "restore_policy_attachment" {
  count = var.enable_long_term_retention ? 1 : 0
  
  role       = aws_iam_role.backup_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

# Create a custom policy for cross-region backup operations if needed
resource "aws_iam_policy" "cross_region_backup_policy" {
  count = var.enable_long_term_retention && local.enable_cross_region ? 1 : 0
  
  name        = "${local.db_identifier}-cross-region-backup-policy"
  description = "Policy for cross-region backup operations"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "rds:CopyDBSnapshot",
          "rds:CopyDBClusterSnapshot",
          "rds:AddTagsToResource"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Attach the cross-region backup policy if cross-region backups are enabled
resource "aws_iam_role_policy_attachment" "cross_region_policy_attachment" {
  count = var.enable_long_term_retention && local.enable_cross_region ? 1 : 0
  
  role       = aws_iam_role.backup_role[0].name
  policy_arn = aws_iam_policy.cross_region_backup_policy[0].arn
  
  depends_on = [
    aws_iam_role.backup_role,
    aws_iam_policy.cross_region_backup_policy
  ]
}

# ------------------------------------------------------------------------------
# SNAPSHOT SCHEDULING AND LIFECYCLE MANAGEMENT
# ------------------------------------------------------------------------------

# Create an EventBridge rule for daily snapshot creation
resource "aws_cloudwatch_event_rule" "daily_snapshot" {
  name                = "${local.db_identifier}-daily-snapshot"
  description         = "Triggers daily snapshots for ${local.db_identifier}"
  schedule_expression = "cron(0 1 * * ? *)"
  
  tags = local.backup_tags
}

# Create an EventBridge target for the snapshot rule
resource "aws_cloudwatch_event_target" "snapshot_target" {
  rule      = aws_cloudwatch_event_rule.daily_snapshot.name
  target_id = "${local.db_identifier}-snapshot"
  arn       = "arn:aws:events:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:event-bus/default"
  
  input = jsonencode({
    source      = "aws.events"
    detail-type = "RDS DB Snapshot Event"
    resources   = [aws_db_instance.postgres_primary.arn]
    detail      = {
      EventCategories = ["backup"]
      SourceType     = "DB_INSTANCE"
      SourceArn      = aws_db_instance.postgres_primary.arn
    }
  })
}

# Create an IAM role for EventBridge to trigger RDS snapshots
resource "aws_iam_role" "snapshot_role" {
  name = "${local.db_identifier}-snapshot-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.backup_tags
}

# Create a policy for EventBridge to create RDS snapshots
resource "aws_iam_policy" "snapshot_policy" {
  name        = "${local.db_identifier}-snapshot-policy"
  description = "Policy for creating RDS snapshots"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "rds:CreateDBSnapshot",
          "rds:AddTagsToResource"
        ]
        Effect   = "Allow"
        Resource = aws_db_instance.postgres_primary.arn
      }
    ]
  })
}

# Attach the snapshot policy to the snapshot role
resource "aws_iam_role_policy_attachment" "snapshot_policy_attachment" {
  role       = aws_iam_role.snapshot_role.name
  policy_arn = aws_iam_policy.snapshot_policy.arn
}

# ------------------------------------------------------------------------------
# LIFECYCLE POLICIES FOR SNAPSHOT MANAGEMENT
# ------------------------------------------------------------------------------

# Create a lifecycle policy for automated snapshot management
resource "aws_dlm_lifecycle_policy" "snapshot_lifecycle" {
  description        = "Lifecycle policy for ${local.db_identifier} snapshots"
  execution_role_arn = aws_iam_role.snapshot_role.arn
  state              = "ENABLED"
  
  policy_details {
    resource_types = ["VOLUME"]
    
    schedule {
      name = "${local.db_identifier}-daily-snapshots"
      
      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["01:00"]
      }
      
      retain_rule {
        count = local.backup_retention_days
      }
      
      copy_tags = true
      
      # Cross-region copy rule for disaster recovery
      dynamic "cross_region_copy_rule" {
        for_each = local.enable_cross_region ? [1] : []
        
        content {
          target    = local.destination_region
          encrypted = var.enable_encryption
          
          retain_rule {
            interval      = 30
            interval_unit = "DAYS"
          }
        }
      }
    }
    
    # Monthly schedule for long-term retention
    dynamic "schedule" {
      for_each = var.enable_long_term_retention ? [1] : []
      
      content {
        name = "${local.db_identifier}-monthly-snapshots"
        
        create_rule {
          interval      = 30
          interval_unit = "DAYS"
          times         = ["01:00"]
        }
        
        retain_rule {
          count = 12 # Keep monthly snapshots for a year
        }
        
        tags_to_add = {
          SnapshotType = "Monthly"
        }
        
        copy_tags = true
      }
    }
    
    target_tags = {
      Name = local.db_identifier
    }
  }
  
  tags = local.backup_tags
}

# ------------------------------------------------------------------------------
# MONITORING AND ALERTING FOR BACKUP OPERATIONS
# ------------------------------------------------------------------------------

# Create a CloudWatch alarm for failed backup operations
resource "aws_cloudwatch_metric_alarm" "backup_failure_alarm" {
  alarm_name          = "${local.db_identifier}-backup-failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FailedBackupCount"
  namespace           = "AWS/RDS"
  period              = "86400" # 24 hours
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This alarm monitors for failed backup operations on ${local.db_identifier}"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_primary.id
  }
  
  tags = local.backup_tags
}

# Create a CloudWatch alarm for backup storage exceeding threshold
resource "aws_cloudwatch_metric_alarm" "backup_storage_alarm" {
  alarm_name          = "${local.db_identifier}-backup-storage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BackupRetentionPeriodStorageUsed"
  namespace           = "AWS/RDS"
  period              = "86400" # 24 hours
  statistic           = "Average"
  threshold           = local.is_production ? "5000" : "2000" # GB
  alarm_description   = "This alarm monitors backup storage usage for ${local.db_identifier}"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres_primary.id
  }
  
  tags = local.backup_tags
}

# ------------------------------------------------------------------------------
# VARIABLES
# ------------------------------------------------------------------------------

variable "enable_cross_region_backup" {
  description = "Whether to enable cross-region backup replication for disaster recovery"
  type        = bool
  default     = false
}

variable "backup_destination_region" {
  description = "The destination region for cross-region backup replication"
  type        = string
  default     = ""
}

variable "cross_region_kms_key_id" {
  description = "KMS key ID in the destination region for encrypted cross-region backups"
  type        = string
  default     = ""
}

variable "enable_long_term_retention" {
  description = "Whether to enable long-term retention of backups (7 years)"
  type        = bool
  default     = false
}

variable "long_term_retention_period" {
  description = "Number of days to retain long-term backups (default: 2555 days = 7 years)"
  type        = number
  default     = 2555
}

# ------------------------------------------------------------------------------
# OUTPUTS
# ------------------------------------------------------------------------------

output "backup_retention_period" {
  description = "The backup retention period in days"
  value       = local.backup_retention_days
}

output "cross_region_backup_enabled" {
  description = "Whether cross-region backup replication is enabled"
  value       = local.enable_cross_region
}

output "cross_region_backup_region" {
  description = "The destination region for cross-region backup replication"
  value       = local.enable_cross_region ? local.destination_region : null
}

output "long_term_retention_enabled" {
  description = "Whether long-term retention is enabled"
  value       = var.enable_long_term_retention
}

output "long_term_retention_period" {
  description = "The long-term retention period in days"
  value       = local.long_term_retention_days
}