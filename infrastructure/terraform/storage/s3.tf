# S3-compatible storage configuration for MCA Application Processing System
# This file defines the S3 buckets used for document storage with appropriate security,
# compliance, and performance settings.

# Production document storage bucket
resource "aws_s3_bucket" "mca_documents_production" {
  # Only create this bucket in production environment
  count  = var.environment == "production" ? 1 : 0
  
  bucket = local.production_bucket_name
  
  # Tags for resource management and cost allocation
  tags = merge(local.common_tags, {
    Environment = "production"
    CostCenter  = "MCA-Production"
  })
  
  # Prevent accidental deletion of production bucket
  lifecycle {
    prevent_destroy = true
  }
}

# Staging document storage bucket
resource "aws_s3_bucket" "mca_documents_staging" {
  # Only create this bucket in staging environment
  count  = var.environment == "staging" ? 1 : 0
  
  bucket = local.staging_bucket_name
  
  # Tags for resource management and cost allocation
  tags = merge(local.common_tags, {
    Environment = "staging"
    CostCenter  = "MCA-Staging"
  })
}

# Server-side encryption configuration with AES-256
resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    # Enforce encryption for all objects
    bucket_key_enabled = true
  }
}

# Enable versioning for document history tracking and compliance
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle rules for document retention and storage optimization
resource "aws_s3_bucket_lifecycle_configuration" "lifecycle_rules" {
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id

  # Rule for transitioning objects to Infrequent Access storage class
  rule {
    id     = "transition-to-ia"
    status = "Enabled"
    
    # Transition objects to Standard-IA after specified days (minimum 30 days)
    transition {
      days          = var.transition_days
      storage_class = "STANDARD_IA"
    }
    
    # Apply rule to all objects
    filter {
      prefix = ""
    }
  }
  
  # Rule for non-current versions (if versioning is enabled)
  rule {
    id     = "manage-noncurrent-versions"
    status = "Enabled"
    
    # Keep non-current versions for compliance
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    
    # Only expire non-current versions if expiration is enabled
    dynamic "noncurrent_version_expiration" {
      for_each = var.expiration_days > 0 ? [1] : []
      content {
        noncurrent_days = var.expiration_days
      }
    }
    
    # Apply rule to all objects
    filter {
      prefix = ""
    }
  }
}

# Block public access to all buckets for security
resource "aws_s3_bucket_public_access_block" "block_public_access" {
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id
  
  # Block all public access
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable request metrics for monitoring
resource "aws_s3_bucket_metrics_configuration" "metrics" {
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id
  
  name = "EntireBucket"
  
  # Filter can be used to track specific prefixes if needed
  filter {
    prefix = ""
  }
}

# Enable server access logging for audit purposes
resource "aws_s3_bucket_logging" "access_logging" {
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id
  
  # Log to a separate logging bucket
  target_bucket = "${var.environment}-logs-bucket"
  target_prefix = "s3-access-logs/"
}

# Configure bucket policy to restrict access to authorized services only
resource "aws_s3_bucket_policy" "bucket_policy" {
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id
  
  # Apply the bucket policy defined in main.tf
  policy = local.bucket_policy
}

# Configure cross-region replication for disaster recovery
resource "aws_s3_bucket_replication_configuration" "replication" {
  # Only enable replication if specified in variables
  count = var.enable_replication ? 1 : 0
  
  # Depends on versioning being enabled
  depends_on = [aws_s3_bucket_versioning.versioning]
  
  # Source bucket
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id
  
  # Role for replication
  role = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/S3ReplicationRole"
  
  # Replication rule
  rule {
    id     = "entire-bucket-replication"
    status = "Enabled"
    
    # Replicate all objects
    filter {
      prefix = ""
    }
    
    # Destination configuration
    destination {
      bucket        = "arn:aws:s3:::${var.environment}-replica-bucket"
      storage_class = "STANDARD"
      
      # Ensure objects are encrypted in the destination bucket
      encryption_configuration {
        replica_kms_key_id = "arn:aws:kms:${var.replica_region}:${data.aws_caller_identity.current.account_id}:key/replica-key-id"
      }
    }
    
    # Source and destination must have versioning enabled
    delete_marker_replication {
      status = "Enabled"
    }
  }
}

# CORS configuration for web access if needed
resource "aws_s3_bucket_cors_configuration" "cors" {
  bucket = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].id : aws_s3_bucket.mca_documents_staging[0].id
  
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["https://*.dollarfunding.com"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Output the bucket names for reference
output "document_bucket_name" {
  description = "Name of the document storage bucket for the current environment"
  value       = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].bucket : aws_s3_bucket.mca_documents_staging[0].bucket
}

# Output the bucket ARNs for IAM policy references
output "document_bucket_arn" {
  description = "ARN of the document storage bucket for the current environment"
  value       = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].arn : aws_s3_bucket.mca_documents_staging[0].arn
}

# Output the bucket domain names for URL construction
output "document_bucket_domain_name" {
  description = "Domain name of the document storage bucket for the current environment"
  value       = var.environment == "production" ? aws_s3_bucket.mca_documents_production[0].bucket_domain_name : aws_s3_bucket.mca_documents_staging[0].bucket_domain_name
}

# Output the bucket region for client configuration
output "document_bucket_region" {
  description = "Region of the document storage bucket for the current environment"
  value       = var.region
}