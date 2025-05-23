# -----------------------------------------------
# Storage Module - S3-Compatible Storage Resources
# -----------------------------------------------
# This module defines the core S3-compatible storage resources for the
# MCA Application Processing System, including production and staging buckets
# with versioning, AES-256 encryption, lifecycle policies, access controls,
# and cross-region replication for disaster recovery.
# -----------------------------------------------

# -----------------------------------------------
# Provider Requirements
# -----------------------------------------------
# This module requires the following provider configuration in the root module:
# 
# provider "aws" {
#   region = "<primary_region>"
# }
# 
# provider "aws" {
#   alias  = "replica"
#   region = "<replica_region>"
# }
# -----------------------------------------------

# -----------------------------------------------
# Local Variables
# -----------------------------------------------

locals {
  # Construct bucket names with proper prefixes and environment
  # Note: S3 bucket names must be globally unique across all AWS accounts
  # Format: dollarfunding-mca-documents-production, dollarfunding-mca-documents-staging
  bucket_name = "${var.bucket_prefix}-${var.project}-${var.bucket_name}-${var.environment}"
  
  # Construct log bucket name if needed
  # Format: dollarfunding-mca-logs-production, dollarfunding-mca-logs-staging
  log_bucket_name = var.access_log_bucket != "" ? var.access_log_bucket : "${var.bucket_prefix}-${var.project}-logs-${var.environment}"
  
  # Common tags for all resources
  common_tags = {
    Environment = var.environment
    Project     = var.project
    ManagedBy   = "terraform"
    Module      = "storage"
  }
  
  # Determine if this is a production environment
  is_production = var.environment == "production"
  
  # Set replica configuration based on environment
  enable_replication = var.enable_replication && length(var.replica_regions) > 0
}

# -----------------------------------------------
# Access Logging Bucket (if enabled)
# -----------------------------------------------

resource "aws_s3_bucket" "logs" {
  count = var.enable_access_logging && var.access_log_bucket == "" ? 1 : 0
  
  bucket = local.log_bucket_name
  force_destroy = var.force_destroy
  
  tags = merge(local.common_tags, {
    Name = "S3 Access Logs"
    Type = "Logs"
  })
}

resource "aws_s3_bucket_lifecycle_configuration" "logs_lifecycle" {
  count = var.enable_access_logging && var.access_log_bucket == "" ? 1 : 0
  
  bucket = aws_s3_bucket.logs[0].id
  
  rule {
    id = "log-expiration"
    status = "Enabled"
    
    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs_encryption" {
  count = var.enable_access_logging && var.access_log_bucket == "" && var.enable_encryption ? 1 : 0
  
  bucket = aws_s3_bucket.logs[0].id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = var.encryption_algorithm
      kms_master_key_id = var.encryption_algorithm == "aws:kms" ? var.kms_key_id : null
    }
  }
}

resource "aws_s3_bucket_public_access_block" "logs_public_access" {
  count = var.enable_access_logging && var.access_log_bucket == "" && var.block_public_access ? 1 : 0
  
  bucket = aws_s3_bucket.logs[0].id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------
# Main Document Storage Bucket
# -----------------------------------------------

resource "aws_s3_bucket" "documents" {
  bucket = local.bucket_name
  force_destroy = var.force_destroy
  
  # Enable object lock if required for compliance
  object_lock_enabled = var.enable_object_lock
  
  tags = merge(local.common_tags, {
    Name = "MCA Document Storage"
    Type = "Documents"
  })
}

# -----------------------------------------------
# Bucket Versioning Configuration
# -----------------------------------------------

resource "aws_s3_bucket_versioning" "documents_versioning" {
  bucket = aws_s3_bucket.documents.id
  
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

# -----------------------------------------------
# Server-Side Encryption Configuration
# -----------------------------------------------

resource "aws_s3_bucket_server_side_encryption_configuration" "documents_encryption" {
  count = var.enable_encryption ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = var.encryption_algorithm
      kms_master_key_id = var.encryption_algorithm == "aws:kms" ? var.kms_key_id : null
    }
    
    # Enforce encryption for all objects
    bucket_key_enabled = var.encryption_algorithm == "aws:kms" ? true : false
  }
}

# -----------------------------------------------
# Lifecycle Configuration
# -----------------------------------------------

resource "aws_s3_bucket_lifecycle_configuration" "documents_lifecycle" {
  count = var.enable_lifecycle_rules ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  
  # This lifecycle configuration depends on versioning being configured first
  depends_on = [aws_s3_bucket_versioning.documents_versioning]
  
  rule {
    id = "document-lifecycle"
    status = "Enabled"
    
    # Ensure minimum retention period for compliance
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
    
    # Transition to infrequent access after specified days
    transition {
      days = max(var.standard_transition_days, var.minimum_retention_days)
      storage_class = var.archive_storage_class
    }
    
    # Transition to glacier if configured
    dynamic "transition" {
      for_each = var.glacier_transition_days > 0 ? [1] : []
      content {
        days = var.glacier_transition_days
        storage_class = "GLACIER"
      }
    }
    
    # Expire objects if configured (0 means never expire)
    dynamic "expiration" {
      for_each = var.expiration_days > 0 ? [1] : []
      content {
        days = max(var.expiration_days, var.minimum_retention_days)
      }
    }
    
    # Handle noncurrent versions
    dynamic "noncurrent_version_transition" {
      for_each = var.enable_versioning ? [1] : []
      content {
        noncurrent_days = 30
        storage_class = var.archive_storage_class
      }
    }
    
    dynamic "noncurrent_version_expiration" {
      for_each = var.enable_versioning && var.noncurrent_version_expiration_days > 0 ? [1] : []
      content {
        noncurrent_days = max(var.noncurrent_version_expiration_days, var.minimum_retention_days)
      }
    }
  }
  
  # Add intelligent tiering rule if enabled
  dynamic "rule" {
    for_each = var.enable_intelligent_tiering ? [1] : []
    content {
      id = "intelligent-tiering"
      status = "Enabled"
      
      filter {
        prefix = ""
      }
      
      transition {
        days = 0
        storage_class = "INTELLIGENT_TIERING"
      }
    }
  }
}

# -----------------------------------------------
# Object Lock Configuration (for compliance)
# -----------------------------------------------

resource "aws_s3_bucket_object_lock_configuration" "documents_object_lock" {
  count = var.enable_object_lock ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  
  rule {
    default_retention {
      mode = var.object_lock_mode
      days = var.object_lock_retention_days
    }
  }
}

# -----------------------------------------------
# Public Access Block Configuration
# -----------------------------------------------

resource "aws_s3_bucket_public_access_block" "documents_public_access" {
  count = var.block_public_access ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------
# Access Logging Configuration
# -----------------------------------------------

resource "aws_s3_bucket_logging" "documents_logging" {
  count = var.enable_access_logging ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  
  target_bucket = var.access_log_bucket != "" ? var.access_log_bucket : aws_s3_bucket.logs[0].id
  target_prefix = "${var.access_log_prefix}${local.bucket_name}/"
}

# -----------------------------------------------
# CORS Configuration
# -----------------------------------------------

resource "aws_s3_bucket_cors_configuration" "documents_cors" {
  count = var.enable_cors ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  
  cors_rule {
    allowed_headers = var.cors_allowed_headers
    allowed_methods = var.cors_allowed_methods
    allowed_origins = var.cors_allowed_origins
    expose_headers  = var.cors_expose_headers
    max_age_seconds = var.cors_max_age_seconds
  }
}

# -----------------------------------------------
# Transfer Acceleration Configuration
# -----------------------------------------------

resource "aws_s3_bucket_accelerate_configuration" "documents_acceleration" {
  count = var.enable_transfer_acceleration ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  status = "Enabled"
}

# -----------------------------------------------
# Request Payment Configuration
# -----------------------------------------------

resource "aws_s3_bucket_request_payment_configuration" "documents_request_payment" {
  bucket = aws_s3_bucket.documents.id
  payer  = "BucketOwner"  # Always have bucket owner pay for requests
}

# -----------------------------------------------
# SSL Enforcement Policy
# -----------------------------------------------

resource "aws_s3_bucket_policy" "documents_ssl_policy" {
  count = var.enable_ssl_requests ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  
  # This policy depends on the public access block being configured first
  depends_on = [aws_s3_bucket_public_access_block.documents_public_access]
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceSSLOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# -----------------------------------------------
# Metrics Configuration
# -----------------------------------------------

resource "aws_s3_bucket_metrics_configuration" "documents_metrics" {
  count = var.enable_request_metrics ? 1 : 0
  
  bucket = aws_s3_bucket.documents.id
  name   = "EntireBucket"
}

# -----------------------------------------------
# Replication Configuration
# -----------------------------------------------

# Create replica buckets in secondary regions if replication is enabled
resource "aws_s3_bucket" "replica" {
  for_each = local.enable_replication ? toset(var.replica_regions) : toset([])
  
  provider = aws.replica
  bucket   = "${local.bucket_name}-replica-${each.value}"
  force_destroy = var.force_destroy
  
  tags = merge(local.common_tags, {
    Name = "MCA Document Storage Replica"
    Type = "DocumentsReplica"
    PrimaryBucket = local.bucket_name
    Region = each.value
  })
}

# Configure versioning on replica buckets
resource "aws_s3_bucket_versioning" "replica_versioning" {
  for_each = local.enable_replication ? toset(var.replica_regions) : toset([])
  
  provider = aws.replica
  bucket   = aws_s3_bucket.replica[each.key].id
  
  versioning_configuration {
    status = "Enabled"  # Replication requires versioning
  }
}

# Configure encryption on replica buckets
resource "aws_s3_bucket_server_side_encryption_configuration" "replica_encryption" {
  for_each = local.enable_replication && var.enable_encryption ? toset(var.replica_regions) : toset([])
  
  provider = aws.replica
  bucket   = aws_s3_bucket.replica[each.key].id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = var.encryption_algorithm
      kms_master_key_id = var.encryption_algorithm == "aws:kms" ? var.kms_key_id : null
    }
    
    bucket_key_enabled = var.encryption_algorithm == "aws:kms" ? true : false
  }
}

# Block public access on replica buckets
resource "aws_s3_bucket_public_access_block" "replica_public_access" {
  for_each = local.enable_replication && var.block_public_access ? toset(var.replica_regions) : toset([])
  
  provider = aws.replica
  bucket   = aws_s3_bucket.replica[each.key].id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM role for replication
resource "aws_iam_role" "replication" {
  count = local.enable_replication ? 1 : 0
  
  name = "s3-bucket-replication-${var.project}-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for replication
resource "aws_iam_policy" "replication" {
  count = local.enable_replication ? 1 : 0
  
  name = "s3-bucket-replication-policy-${var.project}-${var.environment}"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [aws_s3_bucket.documents.arn]
      },
      {
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Effect = "Allow"
        Resource = ["${aws_s3_bucket.documents.arn}/*"]
      },
      {
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Effect = "Allow"
        Resource = [for region in var.replica_regions : "${aws_s3_bucket.replica[region].arn}/*"]
      }
    ]
  })
}

# Attach replication policy to role
resource "aws_iam_role_policy_attachment" "replication" {
  count = local.enable_replication ? 1 : 0
  
  role       = aws_iam_role.replication[0].name
  policy_arn = aws_iam_policy.replication[0].arn
}

# Configure replication on the main bucket
resource "aws_s3_bucket_replication_configuration" "documents_replication" {
  count = local.enable_replication ? 1 : 0
  
  # Must have bucket versioning enabled first
  depends_on = [aws_s3_bucket_versioning.documents_versioning]
  
  role   = aws_iam_role.replication[0].arn
  bucket = aws_s3_bucket.documents.id
  
  dynamic "rule" {
    for_each = toset(var.replica_regions)
    
    content {
      id = "ReplicateTo${rule.key}"
      status = "Enabled"
      
      # Priority when using multiple destination rules
      priority = index(var.replica_regions, rule.key) + 1
      
      # Optional filter to replicate all objects
      filter {}
      
      # Destination bucket configuration
      destination {
        bucket = aws_s3_bucket.replica[rule.key].arn
        storage_class = var.storage_class
        
        # Replicate object ownership
        access_control_translation {
          owner = "Destination"
        }
        
        # Account ID that owns the destination bucket
        account = data.aws_caller_identity.current.account_id
      }
      
      # Replicate delete markers
      delete_marker_replication {
        status = "Enabled"
      }
      
      # Source and destination must have versioning enabled
      source_selection_criteria {
        sse_kms_encrypted_objects {
          status = var.encryption_algorithm == "aws:kms" ? "Enabled" : "Disabled"
        }
      }
    }
  }
}

# -----------------------------------------------
# Data Sources
# -----------------------------------------------

# Get current AWS account ID for replication configuration
data "aws_caller_identity" "current" {}