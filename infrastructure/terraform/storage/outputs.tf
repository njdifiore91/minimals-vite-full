# Outputs from the S3-compatible storage infrastructure

# Re-export outputs from the storage module
output "bucket_name" {
  description = "Name of the S3 bucket for the current environment"
  value       = module.storage.bucket_name
}

output "bucket_arn" {
  description = "ARN of the S3 bucket for the current environment"
  value       = module.storage.bucket_arn
}

output "bucket_domain_name" {
  description = "Domain name of the S3 bucket for the current environment"
  value       = module.storage.bucket_domain_name
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket for the current environment"
  value       = module.storage.bucket_regional_domain_name
}

output "bucket_region" {
  description = "Region of the S3 bucket for the current environment"
  value       = module.storage.bucket_region
}

output "replica_bucket_name" {
  description = "Name of the replica S3 bucket for disaster recovery (if enabled)"
  value       = module.storage.replica_bucket_name
}

output "replica_bucket_arn" {
  description = "ARN of the replica S3 bucket for disaster recovery (if enabled)"
  value       = module.storage.replica_bucket_arn
}

output "replica_bucket_region" {
  description = "Region of the replica S3 bucket for disaster recovery (if enabled)"
  value       = module.storage.replica_bucket_region
}