# JWT Authentication Configuration
# This file configures JWT authentication with RS256 algorithm, including key generation,
# secure storage of private keys, and public key distribution.

# Generate a random ID for key rotation
resource "random_id" "jwt_key_rotation" {
  byte_length = 8
  keepers = {
    # Generate a new key when this value changes
    rotation_timestamp = var.jwt_key_rotation_timestamp
  }
}

# Generate RSA key pair for JWT signing
resource "tls_private_key" "jwt_key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

# Create AWS Secrets Manager secret for JWT private key
resource "aws_secretsmanager_secret" "jwt_private_key" {
  name        = "${local.name_prefix}-jwt-private-key-${random_id.jwt_key_rotation.hex}"
  description = "JWT private key for RS256 signing in ${var.environment} environment"
  tags        = local.common_tags
  
  # Configure recovery window
  recovery_window_in_days = 7
}

# Store JWT private key in AWS Secrets Manager
resource "aws_secretsmanager_secret_version" "jwt_private_key" {
  secret_id     = aws_secretsmanager_secret.jwt_private_key.id
  secret_string = jsonencode({
    private_key = tls_private_key.jwt_key.private_key_pem
    algorithm   = "RS256"
    key_id      = random_id.jwt_key_rotation.hex
    token_expiry_minutes = var.jwt_token_expiry_minutes
    refresh_token_expiry_days = var.jwt_refresh_token_expiry_days
  })
}

# Create AWS Secrets Manager secret for JWT configuration
resource "aws_secretsmanager_secret" "jwt_config" {
  name        = "${local.name_prefix}-jwt-config"
  description = "JWT configuration for ${var.environment} environment"
  tags        = local.common_tags
  
  # Configure recovery window
  recovery_window_in_days = 7
}

# Store JWT configuration in AWS Secrets Manager
resource "aws_secretsmanager_secret_version" "jwt_config" {
  secret_id     = aws_secretsmanager_secret.jwt_config.id
  secret_string = jsonencode({
    current_key_id = random_id.jwt_key_rotation.hex
    algorithm      = "RS256"
    issuer         = "dollarfunding-mca-${var.environment}"
    audience       = "dollarfunding-mca-api"
    token_expiry_minutes = var.jwt_token_expiry_minutes
    refresh_token_expiry_days = var.jwt_refresh_token_expiry_days
  })
}

# Create local file with public key for distribution to services
resource "local_file" "jwt_public_key" {
  content  = tls_private_key.jwt_key.public_key_pem
  filename = "${path.module}/outputs/jwt_public_key_${random_id.jwt_key_rotation.hex}.pem"
  file_permission = "0644"
}

# Create AWS SSM Parameter for JWT public key
resource "aws_ssm_parameter" "jwt_public_key" {
  name        = "/${var.environment}/security/jwt/public_key"
  description = "JWT public key for RS256 verification in ${var.environment} environment"
  type        = "String"
  value       = tls_private_key.jwt_key.public_key_pem
  tags        = local.common_tags
  
  # Overwrite existing parameter
  overwrite   = true
}

# Create IAM policy for JWT key access
resource "aws_iam_policy" "jwt_key_access" {
  name        = "${local.name_prefix}-jwt-key-access"
  description = "Policy for accessing JWT keys in ${var.environment} environment"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue",
        ]
        Effect   = "Allow"
        Resource = [
          aws_secretsmanager_secret.jwt_private_key.arn,
          aws_secretsmanager_secret.jwt_config.arn,
        ]
      },
      {
        Action = [
          "ssm:GetParameter",
        ]
        Effect   = "Allow"
        Resource = [
          aws_ssm_parameter.jwt_public_key.arn,
        ]
      }
    ]
  })
}

# Create directory for outputs if it doesn't exist
resource "null_resource" "create_output_dir" {
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/outputs"
  }
  
  # Run this before creating the local file
  triggers = {
    always_run = timestamp()
  }
}

# Generate Kong JWT plugin configuration
resource "local_file" "kong_jwt_config" {
  content  = templatefile("${path.module}/templates/kong_jwt_config.tpl", {
    public_key = tls_private_key.jwt_key.public_key_pem
    key_id     = random_id.jwt_key_rotation.hex
    algorithm  = "RS256"
  })
  filename = "${path.module}/outputs/kong_jwt_config_${random_id.jwt_key_rotation.hex}.json"
  file_permission = "0644"
  
  depends_on = [null_resource.create_output_dir]
}