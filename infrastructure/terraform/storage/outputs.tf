# outputs.tf for the storage infrastructure
# This file exports output values from the storage module, making them available
# to other Terraform configurations. These outputs provide essential information
# for application services to access the document storage resources.

# Production bucket outputs
output "production_bucket_name" {
  description = "The name of the production document storage bucket"
  value       = module.storage.production_bucket_name
}

output "production_bucket_arn" {
  description = "The ARN of the production document storage bucket for IAM policy references"
  value       = module.storage.production_bucket_arn
}

output "production_bucket_domain_name" {
  description = "The domain name of the production bucket for constructing URLs"
  value       = module.storage.production_bucket_domain_name
}

output "production_bucket_region" {
  description = "The region where the production bucket is located"
  value       = module.storage.production_bucket_region
}

# Staging bucket outputs
output "staging_bucket_name" {
  description = "The name of the staging document storage bucket"
  value       = module.storage.staging_bucket_name
}

output "staging_bucket_arn" {
  description = "The ARN of the staging document storage bucket for IAM policy references"
  value       = module.storage.staging_bucket_arn
}

output "staging_bucket_domain_name" {
  description = "The domain name of the staging bucket for constructing URLs"
  value       = module.storage.staging_bucket_domain_name
}

output "staging_bucket_region" {
  description = "The region where the staging bucket is located"
  value       = module.storage.staging_bucket_region
}

# Replica bucket outputs for disaster recovery
output "production_replica_bucket_name" {
  description = "The name of the production replica bucket for disaster recovery"
  value       = module.storage.production_replica_bucket_name
}

output "production_replica_bucket_arn" {
  description = "The ARN of the production replica bucket for IAM policy references"
  value       = module.storage.production_replica_bucket_arn
}

output "production_replica_bucket_region" {
  description = "The region where the production replica bucket is located"
  value       = module.storage.production_replica_bucket_region
}

output "staging_replica_bucket_name" {
  description = "The name of the staging replica bucket for disaster recovery"
  value       = module.storage.staging_replica_bucket_name
}

output "staging_replica_bucket_arn" {
  description = "The ARN of the staging replica bucket for IAM policy references"
  value       = module.storage.staging_replica_bucket_arn
}

output "staging_replica_bucket_region" {
  description = "The region where the staging replica bucket is located"
  value       = module.storage.staging_replica_bucket_region
}

# Bucket versioning status outputs
output "production_bucket_versioning_enabled" {
  description = "Whether versioning is enabled on the production bucket"
  value       = module.storage.production_bucket_versioning_enabled
}

output "staging_bucket_versioning_enabled" {
  description = "Whether versioning is enabled on the staging bucket"
  value       = module.storage.staging_bucket_versioning_enabled
}

# Bucket encryption outputs
output "production_bucket_encryption_enabled" {
  description = "Whether server-side encryption is enabled on the production bucket"
  value       = module.storage.production_bucket_encryption_enabled
}

output "staging_bucket_encryption_enabled" {
  description = "Whether server-side encryption is enabled on the staging bucket"
  value       = module.storage.staging_bucket_encryption_enabled
}

# Replication configuration outputs
output "production_replication_enabled" {
  description = "Whether cross-region replication is enabled for the production bucket"
  value       = module.storage.production_replication_enabled
}

output "staging_replication_enabled" {
  description = "Whether cross-region replication is enabled for the staging bucket"
  value       = module.storage.staging_replication_enabled
}

# URL generation helper outputs
output "production_bucket_url_base" {
  description = "Base URL for constructing S3 object URLs in the production bucket"
  value       = module.storage.production_bucket_url_base
}

output "staging_bucket_url_base" {
  description = "Base URL for constructing S3 object URLs in the staging bucket"
  value       = module.storage.staging_bucket_url_base
}

# Lifecycle policy outputs
output "production_lifecycle_rules" {
  description = "Summary of lifecycle rules applied to the production bucket"
  value       = module.storage.production_lifecycle_rules
}

output "staging_lifecycle_rules" {
  description = "Summary of lifecycle rules applied to the staging bucket"
  value       = module.storage.staging_lifecycle_rules
}

# Composite outputs for application configuration
output "document_storage_config" {
  description = "Complete document storage configuration for application services"
  value       = module.storage.document_storage_config
}

# Additional outputs for service integration
output "s3_access_point_config" {
  description = "S3 access point configuration for secure service access"
  value = {
    production = {
      access_point_name = module.storage.production_bucket_name
      access_point_arn  = module.storage.production_bucket_arn
      access_point_alias = "${module.storage.production_bucket_name}-ap"
    }
    staging = {
      access_point_name = module.storage.staging_bucket_name
      access_point_arn  = module.storage.staging_bucket_arn
      access_point_alias = "${module.storage.staging_bucket_name}-ap"
    }
  }
}

# Security configuration for document access
output "document_access_security" {
  description = "Security configuration for document access"
  value = {
    encryption_algorithm   = "AES256"
    signed_url_expiration  = 900  # 15 minutes in seconds
    content_disposition    = "attachment"
    allowed_origins        = ["https://*.dollarfunding.com"]
    max_upload_size_mb     = 100
    allowed_content_types  = [
      "application/pdf",
      "image/jpeg",
      "image/png",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
  }
}

# Integration outputs for microservices
output "microservice_integration" {
  description = "Integration configuration for microservices"
  value = {
    document_service = {
      bucket_name = module.storage.production_bucket_name
      bucket_region = module.storage.production_bucket_region
      folder_prefix = "documents/"
    }
    ocr_service = {
      bucket_name = module.storage.production_bucket_name
      bucket_region = module.storage.production_bucket_region
      folder_prefix = "ocr-processing/"
    }
    data_service = {
      bucket_name = module.storage.production_bucket_name
      bucket_region = module.storage.production_bucket_region
      folder_prefix = "application-data/"
    }
  }
}