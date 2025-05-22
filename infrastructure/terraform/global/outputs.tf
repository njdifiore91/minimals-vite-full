# =============================================================================
# Global Terraform Outputs for MCA Application Processing System
# =============================================================================
# This file exports output values from the global Terraform configuration that
# are consumed by environment-specific Terraform configurations. It defines the
# interface between global and environment-specific infrastructure, exposing
# resource IDs, ARNs, and configuration values needed by downstream modules.

# -----------------------------------------------------------------------------
# Network Outputs
# -----------------------------------------------------------------------------

# VPC Outputs
output "global_vpc_id" {
  description = "The ID of the global VPC"
  value       = aws_vpc.global.id
}

output "global_vpc_cidr" {
  description = "The CIDR block of the global VPC"
  value       = aws_vpc.global.cidr_block
}

# Subnet Outputs
output "global_public_subnet_ids" {
  description = "The IDs of the global public subnets"
  value       = [for subnet in aws_subnet.global_public : subnet.id]
}

output "global_private_subnet_ids" {
  description = "The IDs of the global private subnets"
  value       = [for subnet in aws_subnet.global_private : subnet.id]
}

output "global_public_subnet_cidrs" {
  description = "The CIDR blocks of the global public subnets"
  value       = [for subnet in aws_subnet.global_public : subnet.cidr_block]
}

output "global_private_subnet_cidrs" {
  description = "The CIDR blocks of the global private subnets"
  value       = [for subnet in aws_subnet.global_private : subnet.cidr_block]
}

# Transit Gateway Outputs
output "transit_gateway_id" {
  description = "The ID of the transit gateway for inter-environment communication"
  value       = aws_ec2_transit_gateway.main.id
}

output "transit_gateway_route_table_id" {
  description = "The ID of the default transit gateway route table"
  value       = aws_ec2_transit_gateway.main.association_default_route_table_id
}

# Network ACL Outputs
output "global_public_nacl_id" {
  description = "The ID of the network ACL for global public subnets"
  value       = aws_network_acl.global_public.id
}

output "global_private_nacl_ids" {
  description = "The IDs of the network ACLs for global private subnets"
  value       = [for nacl in aws_network_acl.global_private : nacl.id]
}

# -----------------------------------------------------------------------------
# IAM Role and Policy Outputs
# -----------------------------------------------------------------------------

# CI/CD Deployment Role
output "cicd_deployment_role_arn" {
  description = "ARN of the CI/CD deployment role"
  value       = aws_iam_role.cicd_deployment_role.arn
}

# Service-Specific Policy ARNs
output "email_service_policy_arn" {
  description = "ARN of the Email Service policy"
  value       = aws_iam_policy.email_service_policy.arn
}

output "document_service_policy_arn" {
  description = "ARN of the Document Service policy"
  value       = aws_iam_policy.document_service_policy.arn
}

output "ocr_service_policy_arn" {
  description = "ARN of the OCR Service policy"
  value       = aws_iam_policy.ocr_service_policy.arn
}

output "data_service_policy_arn" {
  description = "ARN of the Data Service policy"
  value       = aws_iam_policy.data_service_policy.arn
}

output "notification_service_policy_arn" {
  description = "ARN of the Notification Service policy"
  value       = aws_iam_policy.notification_service_policy.arn
}

# S3 Access Policies
output "s3_document_read_policy_arn" {
  description = "ARN of the S3 document read-only policy"
  value       = aws_iam_policy.s3_document_read_policy.arn
}

output "s3_document_readwrite_policy_arn" {
  description = "ARN of the S3 document read-write policy"
  value       = aws_iam_policy.s3_document_readwrite_policy.arn
}

# OIDC Provider for EKS
output "eks_oidc_provider_arn" {
  description = "ARN of the EKS OIDC provider"
  value       = aws_iam_openid_connect_provider.eks_oidc_provider.arn
}

# JWT Authentication
output "jwt_signing_user_arn" {
  description = "ARN of the JWT signing user"
  value       = aws_iam_user.jwt_signing_user.arn
}

# -----------------------------------------------------------------------------
# Storage Outputs
# -----------------------------------------------------------------------------

# Document Storage Buckets
output "documents_production_bucket_name" {
  description = "The name of the production documents bucket"
  value       = aws_s3_bucket.documents_production.id
}

output "documents_production_bucket_arn" {
  description = "The ARN of the production documents bucket"
  value       = aws_s3_bucket.documents_production.arn
}

output "documents_staging_bucket_name" {
  description = "The name of the staging documents bucket"
  value       = aws_s3_bucket.documents_staging.id
}

output "documents_staging_bucket_arn" {
  description = "The ARN of the staging documents bucket"
  value       = aws_s3_bucket.documents_staging.arn
}

output "documents_development_bucket_name" {
  description = "The name of the development documents bucket"
  value       = aws_s3_bucket.documents_development.id
}

output "documents_development_bucket_arn" {
  description = "The ARN of the development documents bucket"
  value       = aws_s3_bucket.documents_development.arn
}

# Deployment Artifacts Bucket
output "deployment_artifacts_bucket_name" {
  description = "The name of the deployment artifacts bucket"
  value       = aws_s3_bucket.deployment_artifacts.id
}

output "deployment_artifacts_bucket_arn" {
  description = "The ARN of the deployment artifacts bucket"
  value       = aws_s3_bucket.deployment_artifacts.arn
}

# Terraform State Bucket
output "terraform_state_bucket_name" {
  description = "The name of the Terraform state bucket"
  value       = aws_s3_bucket.terraform_state.id
}

output "terraform_state_bucket_arn" {
  description = "The ARN of the Terraform state bucket"
  value       = aws_s3_bucket.terraform_state.arn
}

# -----------------------------------------------------------------------------
# DNS Outputs
# -----------------------------------------------------------------------------

# DNS Zone IDs
output "primary_zone_id" {
  description = "The ID of the primary DNS zone (dollarfunding.com)"
  value       = aws_route53_zone.primary.zone_id
}

output "development_zone_id" {
  description = "The ID of the development DNS zone (dev.dollarfunding.com)"
  value       = aws_route53_zone.development.zone_id
}

output "staging_zone_id" {
  description = "The ID of the staging DNS zone (staging.dollarfunding.com)"
  value       = aws_route53_zone.staging.zone_id
}

output "production_zone_id" {
  description = "The ID of the production DNS zone (app.dollarfunding.com)"
  value       = aws_route53_zone.production.zone_id
}

# DNS Health Check IDs
output "primary_region_health_check_id" {
  description = "The ID of the primary region health check for DNS failover"
  value       = aws_route53_health_check.primary_region.id
}

output "secondary_region_health_check_id" {
  description = "The ID of the secondary region health check for DNS failover"
  value       = aws_route53_health_check.secondary_region.id
}

# -----------------------------------------------------------------------------
# Security Outputs
# -----------------------------------------------------------------------------

# Security Group IDs (assuming these are defined in security.tf)
output "global_security_group_ids" {
  description = "The IDs of the global security groups"
  value       = {
    # These would be defined in security.tf
    # Example: web = aws_security_group.web.id
    # Example: database = aws_security_group.database.id
  }
}

# KMS Key ARNs (assuming these are defined in security.tf)
output "pii_encryption_key_arns" {
  description = "The ARNs of the KMS keys used for PII encryption"
  value       = var.pii_encryption_key_arns
}

output "jwt_signing_key_arns" {
  description = "The ARNs of the KMS keys used for JWT signing"
  value       = var.jwt_signing_key_arns
}

# -----------------------------------------------------------------------------
# Environment CIDR Allocations
# -----------------------------------------------------------------------------

output "development_cidr" {
  description = "The CIDR block allocated for the development environment"
  value       = var.development_cidr
}

output "staging_cidr" {
  description = "The CIDR block allocated for the staging environment"
  value       = var.staging_cidr
}

output "production_cidr" {
  description = "The CIDR block allocated for the production environment"
  value       = var.production_cidr
}