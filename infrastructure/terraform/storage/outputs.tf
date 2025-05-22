# S3 Storage Outputs for MCA Application Processing System
# These outputs provide necessary connection details to application services
# and are essential for integration with the document processing pipeline.

# Production bucket outputs
output "production_bucket_name" {
  description = "Name of the production document storage bucket"
  value       = module.storage.production_bucket_name
}

output "production_bucket_arn" {
  description = "ARN of the production document storage bucket for IAM policy references"
  value       = module.storage.production_bucket_arn
}

output "production_bucket_domain_name" {
  description = "Domain name of the production bucket for constructing URLs"
  value       = module.storage.production_bucket_domain_name
}

output "production_bucket_regional_domain_name" {
  description = "Regional domain name of the production bucket"
  value       = module.storage.production_bucket_regional_domain_name
}

output "production_bucket_region" {
  description = "Region where the production bucket is located"
  value       = module.storage.production_bucket_region
}

# Staging bucket outputs
output "staging_bucket_name" {
  description = "Name of the staging document storage bucket"
  value       = module.storage.staging_bucket_name
}

output "staging_bucket_arn" {
  description = "ARN of the staging document storage bucket for IAM policy references"
  value       = module.storage.staging_bucket_arn
}

output "staging_bucket_domain_name" {
  description = "Domain name of the staging bucket for constructing URLs"
  value       = module.storage.staging_bucket_domain_name
}

output "staging_bucket_regional_domain_name" {
  description = "Regional domain name of the staging bucket"
  value       = module.storage.staging_bucket_regional_domain_name
}

output "staging_bucket_region" {
  description = "Region where the staging bucket is located"
  value       = module.storage.staging_bucket_region
}

# Replica bucket outputs for disaster recovery
output "production_replica_bucket_name" {
  description = "Name of the production replica bucket for disaster recovery"
  value       = module.storage.production_replica_bucket_name
}

output "production_replica_bucket_arn" {
  description = "ARN of the production replica bucket"
  value       = module.storage.production_replica_bucket_arn
}

output "production_replica_bucket_region" {
  description = "Region where the production replica bucket is located"
  value       = module.storage.production_replica_bucket_region
}

output "staging_replica_bucket_name" {
  description = "Name of the staging replica bucket for disaster recovery"
  value       = module.storage.staging_replica_bucket_name
}

output "staging_replica_bucket_arn" {
  description = "ARN of the staging replica bucket"
  value       = module.storage.staging_replica_bucket_arn
}

output "staging_replica_bucket_region" {
  description = "Region where the staging replica bucket is located"
  value       = module.storage.staging_replica_bucket_region
}

# URL generation configuration
output "signed_url_expiration" {
  description = "Default expiration time in seconds for signed URLs (15 minutes)"
  value       = module.storage.signed_url_expiration
}

# Encryption information
output "encryption_algorithm" {
  description = "Encryption algorithm used for bucket objects (AES-256)"
  value       = module.storage.encryption_algorithm
}

# Lifecycle policy information
output "standard_tier_days" {
  description = "Number of days objects remain in standard storage tier before transition"
  value       = module.storage.standard_tier_days
}

output "infrequent_access_tier_days" {
  description = "Number of days objects remain in infrequent access tier before transition"
  value       = module.storage.infrequent_access_tier_days
}

# Access information
output "bucket_access_principals" {
  description = "List of IAM principals with access to the buckets"
  value       = module.storage.bucket_access_principals
  sensitive   = true
}