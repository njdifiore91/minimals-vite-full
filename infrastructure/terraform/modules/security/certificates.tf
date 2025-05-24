# certificates.tf
# This file generates TLS certificates for service-to-service communication
# and stores them securely in AWS Secrets Manager.
#
# Key features:
# - Generates RSA private keys with 4096 bits for strong security
# - Creates self-signed TLS certificates for internal service communication
# - Configures certificates with appropriate validity periods (90 days for production, 365 days for non-prod)
# - Stores certificates and private keys securely in AWS Secrets Manager
# - Implements environment-specific settings (self-signed certificates only in non-production)
# - Supports TLS 1.3 with strong cipher suites for all service-to-service communications

# Generate RSA private key for service TLS certificates
resource "tls_private_key" "service_private_key" {
  algorithm = "RSA"
  rsa_bits  = 4096 # Strong key size for enhanced security
  
  # Only create this resource if we're using self-signed certificates or in non-production
  count = local.use_self_signed ? 1 : 0
}

# Create self-signed TLS certificate for internal service communication
# Only created in non-production environments
resource "tls_self_signed_cert" "service_certificate" {
  # Only create this resource if we're using self-signed certificates or in non-production
  count = local.use_self_signed ? 1 : 0
  
  private_key_pem = tls_private_key.service_private_key[0].private_key_pem

  # Certificate validity period - based on environment
  # Production uses shorter validity periods (90 days) with automated rotation
  # Non-production environments use longer validity (365 days)
  validity_period_hours = local.cert_validity_hours

  # Certificate subject
  subject {
    common_name  = "mca-internal-services.dollarfunding.com"
    organization = "Dollar Funding MCA Services"
    country      = "US"
  }

  # Certificate allowed uses
  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
    "client_auth",
  ]

  # DNS names for the certificate
  # Include all internal service names that will use this certificate
  dns_names = concat(
    # Main domain
    ["mca-internal-services.dollarfunding.com"],
    
    # Service-specific domains for each environment
    [for service in local.service_names : "${service}.${var.environment}.dollarfunding.local"],
    
    # Service-specific domains without environment prefix
    [for service in local.service_names : "${service}.dollarfunding.local"],
    
    # Wildcard for any additional services
    ["*.${var.environment}.dollarfunding.local", "*.dollarfunding.local"]
  )
}

# Store private key in AWS Secrets Manager
resource "aws_secretsmanager_secret" "service_private_key" {
  name        = "mca/tls/${var.environment}/service-private-key"
  description = "TLS private key for MCA service-to-service communication"
  
  # Use customer-managed KMS key for additional security
  kms_key_id  = var.kms_key_id
  
  # Tags for resource management
  tags = merge(var.tags, {
    Name        = "MCA Service Private Key"
    Environment = var.environment
    Service     = "security"
  })
  
  # Only create this resource if we're using self-signed certificates or in non-production
  count = local.use_self_signed ? 1 : 0
}

resource "aws_secretsmanager_secret_version" "service_private_key" {
  secret_id     = aws_secretsmanager_secret.service_private_key[0].id
  secret_string = tls_private_key.service_private_key[0].private_key_pem
  
  # Only create this resource if we're using self-signed certificates or in non-production
  count = local.use_self_signed ? 1 : 0
}

# Store certificate in AWS Secrets Manager
resource "aws_secretsmanager_secret" "service_certificate" {
  name        = "mca/tls/${var.environment}/service-certificate"
  description = "TLS certificate for MCA service-to-service communication"
  
  # Use customer-managed KMS key for additional security
  kms_key_id  = var.kms_key_id
  
  # Tags for resource management
  tags = merge(var.tags, {
    Name        = "MCA Service Certificate"
    Environment = var.environment
    Service     = "security"
  })
  
  # Only create this resource if we're using self-signed certificates or in non-production
  count = local.use_self_signed ? 1 : 0
}

resource "aws_secretsmanager_secret_version" "service_certificate" {
  secret_id     = aws_secretsmanager_secret.service_certificate[0].id
  secret_string = tls_self_signed_cert.service_certificate[0].cert_pem
  
  # Only create this resource if we're using self-signed certificates or in non-production
  count = local.use_self_signed ? 1 : 0
}

# Store certificate and private key together for services that need both
resource "aws_secretsmanager_secret" "service_certificate_bundle" {
  name        = "mca/tls/${var.environment}/service-certificate-bundle"
  description = "TLS certificate and private key bundle for MCA service-to-service communication"
  
  # Use customer-managed KMS key for additional security
  kms_key_id  = var.kms_key_id
  
  # Tags for resource management
  tags = merge(var.tags, {
    Name        = "MCA Service Certificate Bundle"
    Environment = var.environment
    Service     = "security"
  })
  
  # Only create this resource if we're using self-signed certificates or in non-production
  count = local.use_self_signed ? 1 : 0
}

resource "aws_secretsmanager_secret_version" "service_certificate_bundle" {
  secret_id     = aws_secretsmanager_secret.service_certificate_bundle[0].id
  secret_string = jsonencode({
    private_key = tls_private_key.service_private_key[0].private_key_pem
    certificate = tls_self_signed_cert.service_certificate[0].cert_pem
  })
  
  # Only create this resource if we're using self-signed certificates or in non-production
  count = local.use_self_signed ? 1 : 0
}

# Output the certificate ARNs for use in other modules
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

# Variables used in this module
variable "environment" {
  description = "Deployment environment (e.g., development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "kms_key_id" {
  description = "KMS key ID for encrypting secrets in AWS Secrets Manager"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Conditional logic for certificate settings based on environment
locals {
  # In production, certificates should have shorter validity periods
  cert_validity_hours = var.environment == "production" ? 2160 : 8760 # 90 days for prod, 365 days for non-prod
  
  # Determine if self-signed certificates are allowed (only in non-production)
  use_self_signed = var.environment != "production"
  
  # Service names for certificate DNS entries
  service_names = [
    "email-service",
    "document-service",
    "ocr-service",
    "data-service",
    "notification-service",
    "api-gateway",
    "rabbitmq",
    "redis"
  ]
  
  # TLS configuration for services
  tls_config = {
    min_tls_version     = "TLSv1.3" # Enforce TLS 1.3 as minimum version
    cipher_suites       = [
      "TLS_AES_128_GCM_SHA256",       # TLS 1.3 cipher suites
      "TLS_AES_256_GCM_SHA384",
      "TLS_CHACHA20_POLY1305_SHA256"
    ]
  }
}