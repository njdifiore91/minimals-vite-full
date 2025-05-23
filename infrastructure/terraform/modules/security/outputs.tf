# Security Module Outputs
#
# This file defines the outputs from the security module that can be consumed by other modules,
# including IAM role ARNs, KMS key ARNs, JWT public key, S3 encryption configurations, and 
# Secrets Manager ARNs. It enables integration between the security module and other infrastructure components.

# IAM Role Outputs
output "service_role_arns" {
  description = "Map of service names to their IAM role ARNs"
  value       = { for k, v in aws_iam_role.service_roles : k => v.arn }
}

output "service_role_names" {
  description = "Map of service names to their IAM role names"
  value       = { for k, v in aws_iam_role.service_roles : k => v.name }
}

# Individual service role ARNs for direct reference
output "email_service_role_arn" {
  description = "ARN of the IAM role for the Email Service"
  value       = aws_iam_role.service_roles["email-service"].arn
}

output "document_service_role_arn" {
  description = "ARN of the IAM role for the Document Service"
  value       = aws_iam_role.service_roles["document-service"].arn
}

output "ocr_service_role_arn" {
  description = "ARN of the IAM role for the OCR Service"
  value       = aws_iam_role.service_roles["ocr-service"].arn
}

output "data_service_role_arn" {
  description = "ARN of the IAM role for the Data Service"
  value       = aws_iam_role.service_roles["data-service"].arn
}

output "notification_service_role_arn" {
  description = "ARN of the IAM role for the Notification Service"
  value       = aws_iam_role.service_roles["notification-service"].arn
}

output "api_gateway_role_arn" {
  description = "ARN of the IAM role for the API Gateway"
  value       = aws_iam_role.service_roles["api-gateway"].arn
}

# KMS Key Outputs
output "data_encryption_key_arn" {
  description = "ARN of the KMS key used for data encryption (PII fields)"
  value       = aws_kms_key.data_encryption_key.arn
}

output "data_encryption_key_id" {
  description = "ID of the KMS key used for data encryption"
  value       = aws_kms_key.data_encryption_key.key_id
}

output "data_encryption_key_alias" {
  description = "Alias of the KMS key used for data encryption"
  value       = aws_kms_alias.data_encryption_key_alias.name
}

# JWT Authentication Outputs
output "jwt_public_key" {
  description = "The public key for JWT token verification"
  value       = tls_private_key.jwt_key.public_key_pem
}

output "jwt_public_key_path" {
  description = "Path to the JWT public key file"
  value       = local_file.jwt_public_key.filename
}

output "jwt_config_secret_arn" {
  description = "ARN of the JWT configuration secret in AWS Secrets Manager"
  value       = aws_secretsmanager_secret.jwt_config.arn
}

output "jwt_private_key_secret_arn" {
  description = "ARN of the JWT private key secret in AWS Secrets Manager"
  value       = aws_secretsmanager_secret.jwt_private_key.arn
}

output "jwt_config_json_path" {
  description = "Path to the JWT configuration JSON file"
  value       = local_file.jwt_config_json.filename
}

# S3 Encryption Outputs
output "s3_encryption_configuration" {
  description = "Standard S3 encryption configuration for document buckets"
  value = {
    encryption_type    = local.security_settings.s3_encryption_algorithm
    kms_key_id         = local.security_settings.use_kms_encryption ? aws_kms_key.data_encryption_key.arn : null
    bucket_key_enabled = local.security_settings.use_kms_encryption
  }
}

# Security Group Outputs
output "api_gateway_security_group_id" {
  description = "ID of the security group for API Gateway"
  value       = aws_security_group.api_gateway.id
}

output "microservices_security_group_id" {
  description = "ID of the security group for microservices"
  value       = aws_security_group.microservices.id
}

output "database_security_group_id" {
  description = "ID of the security group for database access"
  value       = aws_security_group.database.id
}

# WAF Web ACL Outputs
output "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL for API protection"
  value       = var.enable_waf ? aws_wafv2_web_acl.api_protection[0].arn : null
}

output "waf_web_acl_id" {
  description = "ID of the WAF Web ACL for API protection"
  value       = var.enable_waf ? aws_wafv2_web_acl.api_protection[0].id : null
}

# IAM Policy Outputs
output "s3_document_access_policy_arn" {
  description = "ARN of the IAM policy for S3 document access"
  value       = aws_iam_policy.s3_document_access.arn
}

output "kms_data_access_policy_arn" {
  description = "ARN of the IAM policy for KMS data encryption/decryption"
  value       = aws_iam_policy.kms_data_access.arn
}

output "secrets_access_policy_arn" {
  description = "ARN of the IAM policy for Secrets Manager access"
  value       = aws_iam_policy.secrets_access.arn
}

output "jwt_public_key_access_policy_arn" {
  description = "ARN of the IAM policy for JWT public key access"
  value       = aws_iam_policy.jwt_public_key_access.arn
}

output "jwt_private_key_access_policy_arn" {
  description = "ARN of the IAM policy for JWT private key access"
  value       = aws_iam_policy.jwt_private_key_access.arn
}

# Security Settings Outputs
output "security_settings" {
  description = "Security settings based on environment"
  value       = local.security_settings
}

# Common Tags Output
output "common_tags" {
  description = "Common tags applied to all security resources"
  value       = local.common_tags
}

# Resource Naming Output
output "name_prefix" {
  description = "Resource naming prefix used for all security resources"
  value       = local.name_prefix
}