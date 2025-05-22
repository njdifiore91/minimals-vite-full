# backup.tf - PostgreSQL Database Backup Configuration

# ---------------------------------------------------------------------------------------------------------------------
# AWS Backup Plan for PostgreSQL Database
# Implements automated daily backups with 30-day retention and point-in-time recovery
# ---------------------------------------------------------------------------------------------------------------------

locals {
  # Default to 30 days for backup retention if not specified
  backup_retention_days = try(var.backup_retention_period, 30)
  
  # Default to 7 years (2555 days) for archival retention if not specified
  archival_retention_days = try(var.archival_retention_period, 2555)
  
  # Use the database identifier or a default name
  db_identifier = try(var.identifier, var.name, "postgresql")
  
  # Default tags
  default_tags = {
    Name        = local.db_identifier
    Environment = try(var.environment, "production")
    Terraform   = "true"
  }
}

resource "aws_backup_plan" "postgresql_backup" {
  name = "${local.db_identifier}-backup-plan"

  # Daily backup rule with 30-day retention
  rule {
    rule_name         = "daily-backup-rule"
    target_vault_name = aws_backup_vault.postgresql_backup_vault.name
    schedule          = "cron(0 1 * * ? *)"
    
    # Default to 30 days retention, but allow override through variables
    lifecycle {
      delete_after = local.backup_retention_days
    }

    # Enable continuous backups for point-in-time recovery (5-minute RPO)
    enable_continuous_backup = true

    # Copy actions for cross-region replication
    copy_action {
      destination_vault_arn = aws_backup_vault.postgresql_backup_vault_dr.arn
      lifecycle {
        delete_after = local.backup_retention_days
      }
    }
  }

  # Long-term archival rule for 7-year retention
  rule {
    rule_name         = "archival-backup-rule"
    target_vault_name = aws_backup_vault.postgresql_backup_vault.name
    schedule          = "cron(0 2 1 * ? *)"
    
    # 7-year retention period (2555 days)
    lifecycle {
      delete_after = local.archival_retention_days
    }

    # Copy to DR region for cross-region redundancy
    copy_action {
      destination_vault_arn = aws_backup_vault.postgresql_backup_vault_dr.arn
      lifecycle {
        delete_after = local.archival_retention_days
      }
    }
  }

  tags = merge(
    local.default_tags,
    try(var.tags, {}),
    {
      Name = "${local.db_identifier}-backup-plan"
    },
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# AWS Backup Vault for PostgreSQL Database
# Primary backup storage location
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_backup_vault" "postgresql_backup_vault" {
  name        = "${local.db_identifier}-backup-vault"
  kms_key_arn = try(var.kms_key_arn, null)
  
  tags = merge(
    local.default_tags,
    try(var.tags, {}),
    {
      Name = "${local.db_identifier}-backup-vault"
    },
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# AWS Backup Vault for Disaster Recovery
# Secondary backup storage location in DR region
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_backup_vault" "postgresql_backup_vault_dr" {
  provider    = aws.dr_region
  name        = "${local.db_identifier}-backup-vault-dr"
  kms_key_arn = try(var.dr_kms_key_arn, null)
  
  tags = merge(
    local.default_tags,
    try(var.tags, {}),
    {
      Name = "${local.db_identifier}-backup-vault-dr"
    },
  )
}

# ---------------------------------------------------------------------------------------------------------------------
# AWS Backup Selection for PostgreSQL Database
# Defines which resources are included in the backup plan
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_backup_selection" "postgresql_backup_selection" {
  name          = "${local.db_identifier}-backup-selection"
  iam_role_arn  = aws_iam_role.backup_role.arn
  plan_id       = aws_backup_plan.postgresql_backup.id

  resources = [
    try(var.db_instance_arn, "*")
  ]
}

# ---------------------------------------------------------------------------------------------------------------------
# IAM Role for AWS Backup
# Allows AWS Backup to perform backup and restore operations
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_iam_role" "backup_role" {
  name = "${local.db_identifier}-backup-role"

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

  tags = merge(
    local.default_tags,
    try(var.tags, {}),
    {
      Name = "${local.db_identifier}-backup-role"
    },
  )
}

resource "aws_iam_role_policy_attachment" "backup_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
  role       = aws_iam_role.backup_role.name
}

resource "aws_iam_role_policy_attachment" "restore_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
  role       = aws_iam_role.backup_role.name
}

# Additional policy for RDS point-in-time recovery
resource "aws_iam_role_policy" "rds_pitr_policy" {
  name   = "${local.db_identifier}-rds-pitr-policy"
  role   = aws_iam_role.backup_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rds:RestoreDBInstanceToPointInTime",
          "rds:ModifyDBInstance"
        ]
        Resource = "*"
      }
    ]
  })
}

# ---------------------------------------------------------------------------------------------------------------------
# RDS Instance Automated Backups Replication
# Configures cross-region replication of automated backups
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_db_instance_automated_backups_replication" "postgresql_backup_replication" {
  count = try(var.enable_cross_region_backup, true) ? 1 : 0
  
  provider                = aws.dr_region
  source_db_instance_arn  = try(var.db_instance_arn, "")
  retention_period        = local.backup_retention_days
  kms_key_id              = try(var.dr_kms_key_arn, null)
}

# ---------------------------------------------------------------------------------------------------------------------
# AWS Backup Event Notifications
# Configures SNS notifications for backup events
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_sns_topic" "backup_notifications" {
  count = try(var.enable_backup_notifications, false) ? 1 : 0
  
  name = "${local.db_identifier}-backup-notifications"
  
  tags = merge(
    local.default_tags,
    try(var.tags, {}),
    {
      Name = "${local.db_identifier}-backup-notifications"
    },
  )
}

resource "aws_cloudwatch_event_rule" "backup_event_rule" {
  count = try(var.enable_backup_notifications, false) ? 1 : 0
  
  name        = "${local.db_identifier}-backup-events"
  description = "Capture AWS Backup events for ${local.db_identifier}"
  
  event_pattern = jsonencode({
    source      = ["aws.backup"]
    detail-type = ["Backup Job State Change", "Copy Job State Change", "Restore Job State Change"]
    resources   = [aws_backup_vault.postgresql_backup_vault.arn]
  })
}

resource "aws_cloudwatch_event_target" "backup_event_target" {
  count = try(var.enable_backup_notifications, false) ? 1 : 0
  
  rule      = aws_cloudwatch_event_rule.backup_event_rule[0].name
  target_id = "${local.db_identifier}-backup-notifications"
  arn       = aws_sns_topic.backup_notifications[0].arn
}