# ---------------------------------------------------------------------------------------------------------------------
# GLOBAL TERRAFORM OUTPUTS
# This file exports output values from the global Terraform configuration that are consumed by
# environment-specific Terraform configurations.
# ---------------------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------
# NETWORK OUTPUTS
# Exports network-related resources for use in environment-specific configurations
# ---------------------------------------------------------------------------------------------------------------------

# Global VPC outputs
output "global_vpc_id" {
  description = "ID of the global VPC"
  value       = aws_vpc.global.id
}

output "global_vpc_cidr" {
  description = "CIDR block of the global VPC"
  value       = aws_vpc.global.cidr_block
}

output "global_subnet_ids" {
  description = "IDs of the global VPC subnets"
  value       = aws_subnet.global[*].id
}

# Transit Gateway outputs
output "transit_gateway_id" {
  description = "ID of the transit gateway for inter-environment communication"
  value       = aws_ec2_transit_gateway.main.id
}

output "transit_gateway_route_table_id" {
  description = "ID of the transit gateway route table"
  value       = aws_ec2_transit_gateway_route_table.main.id
}

# VPC Peering Connection outputs
output "vpc_peering_connection_ids" {
  description = "IDs of the VPC peering connections between environments"
  value       = {
    dev_staging        = aws_vpc_peering_connection.dev_staging.id
    staging_production = aws_vpc_peering_connection.staging_production.id
    dev_production     = aws_vpc_peering_connection.dev_production.id
  }
}

# Security Group outputs
output "global_security_group_id" {
  description = "ID of the global security group"
  value       = aws_security_group.global.id
}

# ---------------------------------------------------------------------------------------------------------------------
# IAM ROLE OUTPUTS
# Exports IAM roles and policies for use in environment-specific configurations
# ---------------------------------------------------------------------------------------------------------------------

# Service-specific IAM role ARNs
output "document_service_role_arns" {
  description = "ARNs of the Document Service IAM roles for each environment"
  value       = { for env, role in aws_iam_role.document_service_role : env => role.arn }
}

output "ocr_service_role_arns" {
  description = "ARNs of the OCR Service IAM roles for each environment"
  value       = { for env, role in aws_iam_role.ocr_service_role : env => role.arn }
}

output "email_service_role_arns" {
  description = "ARNs of the Email Service IAM roles for each environment"
  value       = { for env, role in aws_iam_role.email_service_role : env => role.arn }
}

output "data_service_role_arns" {
  description = "ARNs of the Data Service IAM roles for each environment"
  value       = { for env, role in aws_iam_role.data_service_role : env => role.arn }
}

output "notification_service_role_arns" {
  description = "ARNs of the Notification Service IAM roles for each environment"
  value       = { for env, role in aws_iam_role.notification_service_role : env => role.arn }
}

# Cross-account role ARNs
output "cross_account_cicd_role_arns" {
  description = "ARNs of the cross-account CI/CD roles for each environment"
  value       = { for env, role in aws_iam_role.cross_account_cicd_role : env => role.arn }
}

# ---------------------------------------------------------------------------------------------------------------------
# AUTHENTICATION OUTPUTS
# Exports authentication-related resources for use in environment-specific configurations
# ---------------------------------------------------------------------------------------------------------------------

# JWT authentication resources
output "jwt_signing_key_arn" {
  description = "ARN of the KMS key used for JWT signing"
  value       = aws_kms_key.jwt_signing_key.arn
}

output "jwt_config_parameter_name" {
  description = "Name of the SSM parameter containing JWT configuration"
  value       = aws_ssm_parameter.jwt_config.name
}

# ---------------------------------------------------------------------------------------------------------------------
# STORAGE OUTPUTS
# Exports storage-related resources for use in environment-specific configurations
# ---------------------------------------------------------------------------------------------------------------------

# S3 bucket outputs
output "s3_bucket_names" {
  description = "Names of the S3 buckets for document storage in each environment"
  value       = var.s3_bucket_names
}

output "s3_bucket_arns" {
  description = "ARNs of the S3 buckets for document storage in each environment"
  value       = { for env, bucket_name in var.s3_bucket_names : env => "arn:aws:s3:::${bucket_name}" }
}

# ---------------------------------------------------------------------------------------------------------------------
# ENVIRONMENT INFORMATION OUTPUTS
# Exports environment-specific information for use in environment-specific configurations
# ---------------------------------------------------------------------------------------------------------------------

output "environment_account_ids" {
  description = "AWS account IDs for each environment"
  value       = var.environment_account_ids
}

output "aws_region" {
  description = "AWS region where global resources are deployed"
  value       = var.aws_region
}

# ---------------------------------------------------------------------------------------------------------------------
# OIDC PROVIDER OUTPUTS
# Exports OIDC provider ARNs for use in environment-specific configurations
# ---------------------------------------------------------------------------------------------------------------------

output "eks_oidc_provider_arns" {
  description = "ARNs of the OIDC providers for EKS clusters in each environment"
  value       = { for env, provider in aws_iam_openid_connect_provider.eks_oidc_provider : env => provider.arn }
}