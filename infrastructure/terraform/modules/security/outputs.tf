# Security Module - Outputs

# JWT Key Outputs
output "jwt_public_key" {
  description = "Public key for JWT token verification"
  value       = module.jwt_keys.public_key
  sensitive   = false
}

output "jwt_private_key" {
  description = "Private key for JWT token signing"
  value       = module.jwt_keys.private_key
  sensitive   = true
}

# KMS Key Outputs
output "kms_key_id" {
  description = "KMS key ID for data encryption"
  value       = aws_kms_key.data_encryption_key.key_id
}

output "kms_key_arn" {
  description = "KMS key ARN for data encryption"
  value       = aws_kms_key.data_encryption_key.arn
}

# Security Group Outputs
output "api_security_group_id" {
  description = "Security group ID for API Gateway"
  value       = aws_security_group.api_gateway.id
}

output "service_security_group_id" {
  description = "Security group ID for microservices"
  value       = aws_security_group.microservices.id
}

output "database_security_group_id" {
  description = "Security group ID for database access"
  value       = aws_security_group.database.id
}

# IAM Role Outputs
output "service_role_arns" {
  description = "Map of service names to their IAM role ARNs"
  value       = { for k, v in aws_iam_role.service_roles : k => v.arn }
}

# Security Settings
output "security_settings" {
  description = "Security settings based on environment"
  value       = local.security_settings
}

# WAF Web ACL
output "waf_web_acl_arn" {
  description = "WAF Web ACL ARN for API protection"
  value       = var.enable_waf ? aws_wafv2_web_acl.api_protection[0].arn : null
}