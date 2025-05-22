# outputs.tf for the storage module
# This file exports output values from the storage module, including bucket names, ARNs,
# domain names, and access information. These outputs are used by application services
# to access the storage resources and are essential for integration with the document
# processing pipeline.

# Production bucket outputs
output "production_bucket_name" {
  description = "The name of the production document storage bucket"
  value       = aws_s3_bucket.mca_documents_production.id
}

output "production_bucket_arn" {
  description = "The ARN of the production document storage bucket for IAM policy references"
  value       = aws_s3_bucket.mca_documents_production.arn
}

output "production_bucket_domain_name" {
  description = "The domain name of the production bucket for constructing URLs"
  value       = aws_s3_bucket.mca_documents_production.bucket_regional_domain_name
}

output "production_bucket_region" {
  description = "The region where the production bucket is located"
  value       = aws_s3_bucket.mca_documents_production.region
}

# Staging bucket outputs
output "staging_bucket_name" {
  description = "The name of the staging document storage bucket"
  value       = aws_s3_bucket.mca_documents_staging.id
}

output "staging_bucket_arn" {
  description = "The ARN of the staging document storage bucket for IAM policy references"
  value       = aws_s3_bucket.mca_documents_staging.arn
}

output "staging_bucket_domain_name" {
  description = "The domain name of the staging bucket for constructing URLs"
  value       = aws_s3_bucket.mca_documents_staging.bucket_regional_domain_name
}

output "staging_bucket_region" {
  description = "The region where the staging bucket is located"
  value       = aws_s3_bucket.mca_documents_staging.region
}

# Replica bucket outputs for disaster recovery
output "production_replica_bucket_name" {
  description = "The name of the production replica bucket for disaster recovery"
  value       = aws_s3_bucket.mca_documents_production_replica.id
}

output "production_replica_bucket_arn" {
  description = "The ARN of the production replica bucket for IAM policy references"
  value       = aws_s3_bucket.mca_documents_production_replica.arn
}

output "production_replica_bucket_region" {
  description = "The region where the production replica bucket is located"
  value       = var.replica_region
}

output "staging_replica_bucket_name" {
  description = "The name of the staging replica bucket for disaster recovery"
  value       = aws_s3_bucket.mca_documents_staging_replica.id
}

output "staging_replica_bucket_arn" {
  description = "The ARN of the staging replica bucket for IAM policy references"
  value       = aws_s3_bucket.mca_documents_staging_replica.arn
}

output "staging_replica_bucket_region" {
  description = "The region where the staging replica bucket is located"
  value       = var.replica_region
}

# Bucket versioning status outputs
output "production_bucket_versioning_enabled" {
  description = "Whether versioning is enabled on the production bucket"
  value       = aws_s3_bucket_versioning.mca_documents_production.enabled
}

output "staging_bucket_versioning_enabled" {
  description = "Whether versioning is enabled on the staging bucket"
  value       = aws_s3_bucket_versioning.mca_documents_staging.enabled
}

# Bucket encryption outputs
output "production_bucket_encryption_enabled" {
  description = "Whether server-side encryption is enabled on the production bucket"
  value       = aws_s3_bucket_server_side_encryption_configuration.mca_documents_production.rule[0].apply_server_side_encryption_by_default.sse_algorithm == "AES256"
}

output "staging_bucket_encryption_enabled" {
  description = "Whether server-side encryption is enabled on the staging bucket"
  value       = aws_s3_bucket_server_side_encryption_configuration.mca_documents_staging.rule[0].apply_server_side_encryption_by_default.sse_algorithm == "AES256"
}

# Replication configuration outputs
output "production_replication_enabled" {
  description = "Whether cross-region replication is enabled for the production bucket"
  value       = length(aws_s3_bucket_replication_configuration.mca_documents_production.rule) > 0
}

output "staging_replication_enabled" {
  description = "Whether cross-region replication is enabled for the staging bucket"
  value       = length(aws_s3_bucket_replication_configuration.mca_documents_staging.rule) > 0
}

# URL generation helper outputs
output "production_bucket_url_base" {
  description = "Base URL for constructing S3 object URLs in the production bucket"
  value       = "https://${aws_s3_bucket.mca_documents_production.bucket_regional_domain_name}"
}

output "staging_bucket_url_base" {
  description = "Base URL for constructing S3 object URLs in the staging bucket"
  value       = "https://${aws_s3_bucket.mca_documents_staging.bucket_regional_domain_name}"
}

# Lifecycle policy outputs
output "production_lifecycle_rules" {
  description = "Summary of lifecycle rules applied to the production bucket"
  value = {
    transition_to_ia_days = aws_s3_bucket_lifecycle_configuration.mca_documents_production.rule[0].transition[0].days
    expiration_days       = try(aws_s3_bucket_lifecycle_configuration.mca_documents_production.rule[0].expiration[0].days, null)
  }
}

output "staging_lifecycle_rules" {
  description = "Summary of lifecycle rules applied to the staging bucket"
  value = {
    transition_to_ia_days = aws_s3_bucket_lifecycle_configuration.mca_documents_staging.rule[0].transition[0].days
    expiration_days       = try(aws_s3_bucket_lifecycle_configuration.mca_documents_staging.rule[0].expiration[0].days, null)
  }
}

# Composite outputs for application configuration
output "document_storage_config" {
  description = "Complete document storage configuration for application services"
  value = {
    production = {
      bucket_name       = aws_s3_bucket.mca_documents_production.id
      region            = aws_s3_bucket.mca_documents_production.region
      url_base          = "https://${aws_s3_bucket.mca_documents_production.bucket_regional_domain_name}"
      versioning_enabled = aws_s3_bucket_versioning.mca_documents_production.enabled
      replica = {
        bucket_name = aws_s3_bucket.mca_documents_production_replica.id
        region      = var.replica_region
      }
    }
    staging = {
      bucket_name       = aws_s3_bucket.mca_documents_staging.id
      region            = aws_s3_bucket.mca_documents_staging.region
      url_base          = "https://${aws_s3_bucket.mca_documents_staging.bucket_regional_domain_name}"
      versioning_enabled = aws_s3_bucket_versioning.mca_documents_staging.enabled
      replica = {
        bucket_name = aws_s3_bucket.mca_documents_staging_replica.id
        region      = var.replica_region
      }
    }
    security = {
      encryption_algorithm = "AES256"
      signed_url_expiration = 900  # 15 minutes in seconds
    }
  }
}