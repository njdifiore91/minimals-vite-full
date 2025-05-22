# Outputs from the security module

# JWT Authentication Outputs
output "jwt_public_key" {
  description = "JWT public key for RS256 verification"
  value       = tls_private_key.jwt_key.public_key_pem
  sensitive   = false
}

output "jwt_public_key_id" {
  description = "Unique identifier for the current JWT key pair"
  value       = random_id.jwt_key_rotation.hex
  sensitive   = false
}

output "jwt_private_key_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing the JWT private key"
  value       = aws_secretsmanager_secret.jwt_private_key.arn
  sensitive   = false
}

output "jwt_config_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing the JWT configuration"
  value       = aws_secretsmanager_secret.jwt_config.arn
  sensitive   = false
}

output "jwt_public_key_ssm_parameter_name" {
  description = "Name of the SSM parameter containing the JWT public key"
  value       = aws_ssm_parameter.jwt_public_key.name
  sensitive   = false
}

output "jwt_key_access_policy_arn" {
  description = "ARN of the IAM policy for JWT key access"
  value       = aws_iam_policy.jwt_key_access.arn
  sensitive   = false
}

# JWT Configuration Outputs
output "jwt_token_expiry_minutes" {
  description = "JWT token expiry time in minutes"
  value       = var.jwt_token_expiry_minutes
  sensitive   = false
}

output "jwt_refresh_token_expiry_days" {
  description = "JWT refresh token expiry time in days"
  value       = var.jwt_refresh_token_expiry_days
  sensitive   = false
}

# Kong JWT Configuration Output
output "kong_jwt_config_path" {
  description = "Path to the Kong JWT configuration file"
  value       = local_file.kong_jwt_config.filename
  sensitive   = false
}

# S3 Encryption Outputs
output "s3_encryption_type" {
  description = "Type of encryption used for S3 buckets"
  value       = var.s3_encryption_type
  sensitive   = false
}

output "s3_kms_key_arn" {
  description = "ARN of the KMS key used for S3 encryption"
  value       = var.s3_encryption_type == "aws:kms" ? aws_kms_key.s3_encryption[0].arn : null
  sensitive   = false
}

output "s3_kms_key_id" {
  description = "ID of the KMS key used for S3 encryption"
  value       = var.s3_encryption_type == "aws:kms" ? aws_kms_key.s3_encryption[0].key_id : null
  sensitive   = false
}

output "s3_kms_access_policy_arn" {
  description = "ARN of the IAM policy for accessing the S3 KMS key"
  value       = var.s3_encryption_type == "aws:kms" ? aws_iam_policy.s3_kms_access[0].arn : null
  sensitive   = false
}