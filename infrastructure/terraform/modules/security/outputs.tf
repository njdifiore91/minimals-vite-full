# outputs.tf
# This file defines the outputs from the security module that can be consumed by other modules
# It includes IAM role ARNs, KMS key ARNs, JWT public key, S3 encryption configurations, and Secrets Manager ARNs

# ---------------------------------------------------------------------------------------------------------------------
# IAM ROLE OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "email_service_role_arn" {
  description = "ARN of the IAM role for the Email Service"
  value       = aws_iam_role.email_service.arn
}

output "document_service_role_arn" {
  description = "ARN of the IAM role for the Document Service"
  value       = aws_iam_role.document_service.arn
}

output "ocr_service_role_arn" {
  description = "ARN of the IAM role for the OCR Service"
  value       = aws_iam_role.ocr_service.arn
}

output "data_service_role_arn" {
  description = "ARN of the IAM role for the Data Service"
  value       = aws_iam_role.data_service.arn
}

output "notification_service_role_arn" {
  description = "ARN of the IAM role for the Notification Service"
  value       = aws_iam_role.notification_service.arn
}

output "api_gateway_role_arn" {
  description = "ARN of the IAM role for the API Gateway"
  value       = aws_iam_role.api_gateway.arn
}

# ---------------------------------------------------------------------------------------------------------------------
# IAM POLICY OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "s3_document_access_policy_arn" {
  description = "ARN of the IAM policy for S3 document access"
  value       = aws_iam_policy.s3_document_access.arn
}

output "s3_document_read_only_policy_arn" {
  description = "ARN of the IAM policy for S3 document read-only access"
  value       = aws_iam_policy.s3_document_read_only.arn
}

output "kms_pii_access_policy_arn" {
  description = "ARN of the IAM policy for KMS PII access"
  value       = aws_iam_policy.kms_pii_access.arn
}

output "s3_kms_access_policy_arn" {
  description = "ARN of the IAM policy for S3 KMS access"
  value       = var.s3_encryption_type == "aws:kms" ? aws_iam_policy.s3_kms_access[0].arn : null
}

output "jwt_key_access_policy_arn" {
  description = "ARN of the IAM policy for JWT key access"
  value       = aws_iam_policy.jwt_key_access.arn
}

# ---------------------------------------------------------------------------------------------------------------------
# KMS KEY OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "pii_encryption_key_id" {
  description = "ID of the KMS key used for PII field-level encryption"
  value       = aws_kms_key.pii_encryption.key_id
}

output "pii_encryption_key_arn" {
  description = "ARN of the KMS key used for PII field-level encryption"
  value       = aws_kms_key.pii_encryption.arn
}

output "s3_encryption_key_id" {
  description = "ID of the KMS key used for S3 bucket encryption"
  value       = var.s3_encryption_type == "aws:kms" ? aws_kms_key.s3_encryption[0].key_id : null
}

output "s3_encryption_key_arn" {
  description = "ARN of the KMS key used for S3 bucket encryption"
  value       = var.s3_encryption_type == "aws:kms" ? aws_kms_key.s3_encryption[0].arn : null
}

# ---------------------------------------------------------------------------------------------------------------------
# S3 ENCRYPTION OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "s3_encryption_type" {
  description = "Type of encryption used for S3 buckets"
  value       = var.s3_encryption_type
}

output "s3_encryption_configuration" {
  description = "S3 bucket encryption configuration"
  value       = {
    encryption_type = var.s3_encryption_type
    kms_key_id      = var.s3_encryption_type == "aws:kms" ? aws_kms_key.s3_encryption[0].key_id : null
    bucket_key_enabled = true
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# JWT AUTHENTICATION OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "jwt_public_key" {
  description = "Public key for JWT verification"
  value       = tls_private_key.jwt_key.public_key_pem
  sensitive   = false
}

output "jwt_public_key_ssm_parameter" {
  description = "SSM parameter name for the JWT public key"
  value       = aws_ssm_parameter.jwt_public_key.name
}

output "jwt_private_key_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the JWT private key"
  value       = aws_secretsmanager_secret.jwt_private_key.arn
  sensitive   = true
}

output "jwt_config_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the JWT configuration"
  value       = aws_secretsmanager_secret.jwt_config.arn
}

output "jwt_key_id" {
  description = "Current JWT key ID for key rotation"
  value       = random_id.jwt_key_rotation.hex
}

# ---------------------------------------------------------------------------------------------------------------------
# SECRETS MANAGER OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "rabbitmq_credentials_secret_arn" {
  description = "ARN of the RabbitMQ credentials secret"
  value       = aws_secretsmanager_secret.rabbitmq_credentials.arn
}

output "redis_credentials_secret_arn" {
  description = "ARN of the Redis credentials secret"
  value       = aws_secretsmanager_secret.redis_credentials.arn
}

output "email_service_credentials_secret_arn" {
  description = "ARN of the email service credentials secret"
  value       = aws_secretsmanager_secret.email_service_credentials.arn
}

output "webhook_hmac_key_secret_arn" {
  description = "ARN of the webhook HMAC key secret"
  value       = aws_secretsmanager_secret.webhook_hmac_key.arn
}

output "customer_webhook_hmac_key_secret_arns" {
  description = "Map of customer IDs to ARNs of their webhook HMAC key secrets"
  value       = { for k, v in aws_secretsmanager_secret.customer_webhook_hmac_key : k => v.arn }
}

# ---------------------------------------------------------------------------------------------------------------------
# TLS CERTIFICATE OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "certificate_secret_arn" {
  description = "ARN of the certificate secret in AWS Secrets Manager"
  value       = local.use_self_signed ? aws_secretsmanager_secret.service_certificate[0].arn : null
}

output "private_key_secret_arn" {
  description = "ARN of the private key secret in AWS Secrets Manager"
  value       = local.use_self_signed ? aws_secretsmanager_secret.service_private_key[0].arn : null
}

output "certificate_bundle_secret_arn" {
  description = "ARN of the certificate bundle secret in AWS Secrets Manager"
  value       = local.use_self_signed ? aws_secretsmanager_secret.service_certificate_bundle[0].arn : null
}

output "tls_config" {
  description = "TLS configuration settings for services"
  value       = local.tls_config
}

# ---------------------------------------------------------------------------------------------------------------------
# API GATEWAY SECURITY OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "api_gateway_jwt_config_path" {
  description = "Path to the generated JWT configuration file for API Gateway"
  value       = local_file.jwt_config.filename
}

output "api_gateway_cors_config_path" {
  description = "Path to the generated CORS configuration file for API Gateway"
  value       = local_file.cors_config.filename
}

output "api_gateway_rate_limiting_configs" {
  description = "Paths to the generated rate limiting configuration files for API Gateway"
  value = {
    admin         = local_file.rate_limiting_admin_config.filename
    operations    = local_file.rate_limiting_operations_config.filename
    authenticated = local_file.rate_limiting_authenticated_config.filename
    unauthenticated = local_file.rate_limiting_unauthenticated_config.filename
  }
}

output "api_gateway_ip_restriction_config_path" {
  description = "Path to the generated IP restriction configuration file for API Gateway"
  value       = local_file.ip_restriction_config.filename
}

output "api_gateway_security_headers" {
  description = "Security headers configuration for API Gateway"
  value       = local.security_headers
}

# ---------------------------------------------------------------------------------------------------------------------
# SECURITY MODULE METADATA
# ---------------------------------------------------------------------------------------------------------------------

output "security_module_version" {
  description = "Version of the security module"
  value       = "1.0.0"
}

output "environment" {
  description = "Environment for which the security resources are configured"
  value       = var.environment
}