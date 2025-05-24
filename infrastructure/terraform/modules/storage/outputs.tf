# -----------------------------------------------
# Storage Module Outputs
# -----------------------------------------------
# This file defines all output values from the storage module, including
# bucket names, ARNs, domain names, and access information. These outputs
# are used by application services to access the storage resources and
# are essential for integration with the document processing pipeline.
# -----------------------------------------------

# -----------------------------------------------
# Production Bucket Outputs
# -----------------------------------------------

output "production_bucket_name" {
  description = "Name of the production document storage bucket"
  value       = aws_s3_bucket.mca_documents_production.id
}

output "production_bucket_arn" {
  description = "ARN of the production document storage bucket"
  value       = aws_s3_bucket.mca_documents_production.arn
}

output "production_bucket_domain_name" {
  description = "Domain name of the production document storage bucket"
  value       = aws_s3_bucket.mca_documents_production.bucket_domain_name
}

output "production_bucket_regional_domain_name" {
  description = "Regional domain name of the production document storage bucket"
  value       = aws_s3_bucket.mca_documents_production.bucket_regional_domain_name
}

output "production_bucket_region" {
  description = "Region of the production document storage bucket"
  value       = var.primary_region
}

# -----------------------------------------------
# Staging Bucket Outputs
# -----------------------------------------------

output "staging_bucket_name" {
  description = "Name of the staging document storage bucket"
  value       = aws_s3_bucket.mca_documents_staging.id
}

output "staging_bucket_arn" {
  description = "ARN of the staging document storage bucket"
  value       = aws_s3_bucket.mca_documents_staging.arn
}

output "staging_bucket_domain_name" {
  description = "Domain name of the staging document storage bucket"
  value       = aws_s3_bucket.mca_documents_staging.bucket_domain_name
}

output "staging_bucket_regional_domain_name" {
  description = "Regional domain name of the staging document storage bucket"
  value       = aws_s3_bucket.mca_documents_staging.bucket_regional_domain_name
}

output "staging_bucket_region" {
  description = "Region of the staging document storage bucket"
  value       = var.primary_region
}

# -----------------------------------------------
# Replica Bucket Outputs (if enabled)
# -----------------------------------------------

output "production_replica_bucket_name" {
  description = "Name of the production replica document storage bucket"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? aws_s3_bucket.mca_documents_production_replica[0].id : null
}

output "production_replica_bucket_arn" {
  description = "ARN of the production replica document storage bucket"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? aws_s3_bucket.mca_documents_production_replica[0].arn : null
}

output "production_replica_bucket_domain_name" {
  description = "Domain name of the production replica document storage bucket"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? aws_s3_bucket.mca_documents_production_replica[0].bucket_domain_name : null
}

output "production_replica_bucket_region" {
  description = "Region of the production replica document storage bucket"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? local.replica_region : null
}

output "staging_replica_bucket_name" {
  description = "Name of the staging replica document storage bucket"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? aws_s3_bucket.mca_documents_staging_replica[0].id : null
}

output "staging_replica_bucket_arn" {
  description = "ARN of the staging replica document storage bucket"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? aws_s3_bucket.mca_documents_staging_replica[0].arn : null
}

output "staging_replica_bucket_domain_name" {
  description = "Domain name of the staging replica document storage bucket"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? aws_s3_bucket.mca_documents_staging_replica[0].bucket_domain_name : null
}

output "staging_replica_bucket_region" {
  description = "Region of the staging replica document storage bucket"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? local.replica_region : null
}

# -----------------------------------------------
# Access Logging Bucket Outputs (if created)
# -----------------------------------------------

output "access_log_bucket_name" {
  description = "Name of the access logging bucket (if created)"
  value       = var.enable_access_logging && var.access_log_bucket == "" ? aws_s3_bucket.access_logs[0].id : var.access_log_bucket
}

output "access_log_bucket_arn" {
  description = "ARN of the access logging bucket (if created)"
  value       = var.enable_access_logging && var.access_log_bucket == "" ? aws_s3_bucket.access_logs[0].arn : null
}

# -----------------------------------------------
# URL Generation Helper Outputs
# -----------------------------------------------

output "production_bucket_url_prefix" {
  description = "URL prefix for production bucket objects (without protocol)"
  value       = "${aws_s3_bucket.mca_documents_production.bucket_regional_domain_name}/"
}

output "staging_bucket_url_prefix" {
  description = "URL prefix for staging bucket objects (without protocol)"
  value       = "${aws_s3_bucket.mca_documents_staging.bucket_regional_domain_name}/"
}

output "production_replica_bucket_url_prefix" {
  description = "URL prefix for production replica bucket objects (without protocol)"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? "${aws_s3_bucket.mca_documents_production_replica[0].bucket_regional_domain_name}/" : null
}

output "staging_replica_bucket_url_prefix" {
  description = "URL prefix for staging replica bucket objects (without protocol)"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? "${aws_s3_bucket.mca_documents_staging_replica[0].bucket_regional_domain_name}/" : null
}

# -----------------------------------------------
# Configuration Outputs
# -----------------------------------------------

output "encryption_algorithm" {
  description = "Server-side encryption algorithm used for buckets"
  value       = var.encryption_algorithm
}

output "versioning_enabled" {
  description = "Whether versioning is enabled for the buckets"
  value       = var.enable_versioning
}

output "replication_enabled" {
  description = "Whether cross-region replication is enabled"
  value       = var.enable_replication && length(var.replica_regions) > 0
}

output "signed_url_expiration" {
  description = "Default expiration time in seconds for signed URLs"
  value       = var.signed_url_expiration
}

# -----------------------------------------------
# IAM Role Outputs (for replication)
# -----------------------------------------------

output "replication_role_arn" {
  description = "ARN of the IAM role used for bucket replication"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? aws_iam_role.replication[0].arn : null
}

output "replication_role_name" {
  description = "Name of the IAM role used for bucket replication"
  value       = var.enable_replication && length(var.replica_regions) > 0 ? aws_iam_role.replication[0].name : null
}

# -----------------------------------------------
# Consolidated Outputs (for easier consumption)
# -----------------------------------------------

output "bucket_info" {
  description = "Consolidated information about all buckets for easier consumption"
  value = {
    production = {
      name            = aws_s3_bucket.mca_documents_production.id
      arn             = aws_s3_bucket.mca_documents_production.arn
      domain_name     = aws_s3_bucket.mca_documents_production.bucket_domain_name
      regional_domain = aws_s3_bucket.mca_documents_production.bucket_regional_domain_name
      region          = var.primary_region
      url_prefix      = "${aws_s3_bucket.mca_documents_production.bucket_regional_domain_name}/"
    },
    staging = {
      name            = aws_s3_bucket.mca_documents_staging.id
      arn             = aws_s3_bucket.mca_documents_staging.arn
      domain_name     = aws_s3_bucket.mca_documents_staging.bucket_domain_name
      regional_domain = aws_s3_bucket.mca_documents_staging.bucket_regional_domain_name
      region          = var.primary_region
      url_prefix      = "${aws_s3_bucket.mca_documents_staging.bucket_regional_domain_name}/"
    },
    replica = var.enable_replication && length(var.replica_regions) > 0 ? {
      production = {
        name            = aws_s3_bucket.mca_documents_production_replica[0].id
        arn             = aws_s3_bucket.mca_documents_production_replica[0].arn
        domain_name     = aws_s3_bucket.mca_documents_production_replica[0].bucket_domain_name
        regional_domain = aws_s3_bucket.mca_documents_production_replica[0].bucket_regional_domain_name
        region          = local.replica_region
        url_prefix      = "${aws_s3_bucket.mca_documents_production_replica[0].bucket_regional_domain_name}/"
      },
      staging = {
        name            = aws_s3_bucket.mca_documents_staging_replica[0].id
        arn             = aws_s3_bucket.mca_documents_staging_replica[0].arn
        domain_name     = aws_s3_bucket.mca_documents_staging_replica[0].bucket_domain_name
        regional_domain = aws_s3_bucket.mca_documents_staging_replica[0].bucket_regional_domain_name
        region          = local.replica_region
        url_prefix      = "${aws_s3_bucket.mca_documents_staging_replica[0].bucket_regional_domain_name}/"
      }
    } : null
  }
}

# -----------------------------------------------
# Module Compliance Notes
# -----------------------------------------------
# This outputs file implements the following requirements from the technical specification:
#
# 1. Export bucket names for production and staging environments
#    - Production and staging bucket names are exported as separate outputs
#    - Consolidated bucket information is provided in the bucket_info output
#
# 2. Output bucket ARNs for IAM policy references
#    - ARNs for all buckets are exported for use in IAM policies
#    - These are essential for configuring secure access to the buckets
#
# 3. Provide bucket domain names for constructing URLs
#    - Both standard and regional domain names are exported
#    - URL prefixes are provided for easy construction of object URLs
#
# 4. Export bucket region information for client configuration
#    - Region information is included for all buckets
#    - This enables proper client configuration for regional endpoints
#
# 5. Include replica bucket details for disaster recovery scenarios
#    - Replica bucket information is exported when replication is enabled
#    - This supports disaster recovery and multi-region access patterns
#
# Additional outputs provided:
# - Access logging bucket information (if created)
# - Encryption and versioning configuration details
# - IAM role information for replication
# - Consolidated bucket information for easier consumption by other modules