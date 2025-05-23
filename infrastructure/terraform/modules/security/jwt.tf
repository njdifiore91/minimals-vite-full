# JWT Authentication Configuration for MCA Application Processing System
# This file implements JWT authentication with RS256 algorithm, including key generation,
# secure storage of private keys, and public key distribution.

# Variables for JWT configuration
variable "jwt_issuer" {
  description = "The issuer claim for JWT tokens"
  type        = string
  default     = "https://api.dollarfunding.com"
}

variable "jwt_audience" {
  description = "The audience claim for JWT tokens"
  type        = string
  default     = "mca-application-processing"
}

variable "enable_jwt_key_rotation" {
  description = "Whether to enable automatic JWT key rotation"
  type        = bool
  default     = true
}

variable "jwt_key_rotation_lambda_arn" {
  description = "ARN of the Lambda function to handle JWT key rotation"
  type        = string
  default     = ""
}

# Generate RSA key pair for JWT signing
resource "tls_private_key" "jwt_key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

# Create a secret in AWS Secrets Manager to store the private key
resource "aws_secretsmanager_secret" "jwt_private_key" {
  name        = "${local.name_prefix}-jwt-private-key"
  description = "JWT private key for API authentication (RS256)"
  
  # Use KMS key for additional encryption if available
  kms_key_id  = aws_kms_key.data_encryption_key.id
  
  # Set recovery window based on environment
  recovery_window_in_days = local.is_production ? 30 : 7
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-jwt-private-key"
      Type = "JWT-Authentication"
    },
    var.resource_tags
  )
}

# Store the private key in the secret
resource "aws_secretsmanager_secret_version" "jwt_private_key" {
  secret_id     = aws_secretsmanager_secret.jwt_private_key.id
  secret_string = jsonencode({
    private_key = tls_private_key.jwt_key.private_key_pem,
    algorithm   = "RS256",
    key_id      = "${local.name_prefix}-jwt-key",
    created_at  = timestamp(),
    token_expiry_minutes = local.security_settings.jwt_token_expiry,
    refresh_token_expiry_days = local.security_settings.jwt_refresh_expiry,
    issuer      = var.jwt_issuer,
    audience    = var.jwt_audience
  })
}

# Save public key to a local file for distribution to services
resource "local_file" "jwt_public_key" {
  depends_on = [null_resource.create_output_dir]
  
  content  = tls_private_key.jwt_key.public_key_pem
  filename = "${path.module}/outputs/${local.name_prefix}-jwt-public-key.pem"
  file_permission = "0644"
}

# Create a secret for storing the JWT configuration
resource "aws_secretsmanager_secret" "jwt_config" {
  name        = "${local.name_prefix}-jwt-config"
  description = "JWT configuration for API authentication"
  
  # Use KMS key for additional encryption
  kms_key_id  = aws_kms_key.data_encryption_key.id
  
  # Set recovery window based on environment
  recovery_window_in_days = local.is_production ? 30 : 7
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-jwt-config"
      Type = "JWT-Authentication"
    },
    var.resource_tags
  )
}

# Store the JWT configuration in the secret
resource "aws_secretsmanager_secret_version" "jwt_config" {
  secret_id     = aws_secretsmanager_secret.jwt_config.id
  secret_string = jsonencode({
    algorithm   = "RS256",
    key_id      = "${local.name_prefix}-jwt-key",
    issuer      = var.jwt_issuer,
    audience    = var.jwt_audience,
    token_expiry_minutes = local.security_settings.jwt_token_expiry,
    refresh_token_expiry_days = local.security_settings.jwt_refresh_expiry,
    public_key  = tls_private_key.jwt_key.public_key_pem
  })
}

# Create a directory for output files if it doesn't exist
resource "null_resource" "create_output_dir" {
  # This will run on every apply, but that's fine as mkdir -p is idempotent
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/outputs"
  }
  
  # Add a trigger to ensure this runs before the files are created
  triggers = {
    always_run = timestamp()
  }
}

# Create a JSON file with JWT configuration for Kong API Gateway
resource "local_file" "jwt_config_json" {
  depends_on = [null_resource.create_output_dir]
  
  content  = jsonencode({
    algorithm   = "RS256",
    key_id      = "${local.name_prefix}-jwt-key",
    issuer      = var.jwt_issuer,
    audience    = var.jwt_audience,
    token_expiry_minutes = local.security_settings.jwt_token_expiry,
    refresh_token_expiry_days = local.security_settings.jwt_refresh_expiry,
    public_key  = tls_private_key.jwt_key.public_key_pem
  })
  filename = "${path.module}/outputs/${local.name_prefix}-jwt-config.json"
  file_permission = "0644"
}

# Schedule key rotation using AWS EventBridge if enabled
resource "aws_cloudwatch_event_rule" "jwt_key_rotation" {
  count = var.enable_jwt_key_rotation && var.jwt_key_rotation_lambda_arn != "" ? 1 : 0
  
  name        = "${local.name_prefix}-jwt-key-rotation"
  description = "Trigger JWT key rotation based on schedule"
  
  # Schedule based on environment (more frequent in production)
  schedule_expression = "rate(${local.security_settings.jwt_key_rotation_days} days)"
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-jwt-key-rotation"
      Type = "JWT-Authentication"
    },
    var.resource_tags
  )
}

# Lambda function target for key rotation (if enabled)
resource "aws_cloudwatch_event_target" "jwt_key_rotation" {
  count = var.enable_jwt_key_rotation && var.jwt_key_rotation_lambda_arn != "" ? 1 : 0
  
  rule      = aws_cloudwatch_event_rule.jwt_key_rotation[0].name
  target_id = "${local.name_prefix}-jwt-key-rotation"
  arn       = var.jwt_key_rotation_lambda_arn
  
  input = jsonencode({
    secretName = aws_secretsmanager_secret.jwt_private_key.name,
    configName = aws_secretsmanager_secret.jwt_config.name,
    algorithm  = "RS256",
    keyId      = "${local.name_prefix}-jwt-key",
    rsaBits    = 2048
  })
}

# IAM policy for services to access JWT public key
resource "aws_iam_policy" "jwt_public_key_access" {
  name        = "${local.name_prefix}-jwt-public-key-access"
  description = "Policy to allow services to access JWT public key configuration"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          aws_secretsmanager_secret.jwt_config.arn
        ]
      }
    ]
  })
}

# IAM policy for authentication service to access JWT private key
resource "aws_iam_policy" "jwt_private_key_access" {
  name        = "${local.name_prefix}-jwt-private-key-access"
  description = "Policy to allow authentication service to access JWT private key"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          aws_secretsmanager_secret.jwt_private_key.arn,
          aws_secretsmanager_secret.jwt_config.arn
        ]
      }
    ]
  })
}

# Attach JWT public key access policy to service roles that need to validate tokens
resource "aws_iam_role_policy_attachment" "jwt_public_key_access" {
  for_each = toset([
    "api-gateway",
    "data-service",
    "document-service",
    "ocr-service",
    "notification-service",
    "email-service"
  ])
  
  role       = aws_iam_role.service_roles[each.key].name
  policy_arn = aws_iam_policy.jwt_public_key_access.arn
}

# Attach JWT private key access policy only to the API Gateway (authentication service)
resource "aws_iam_role_policy_attachment" "jwt_private_key_access" {
  role       = aws_iam_role.service_roles["api-gateway"].name
  policy_arn = aws_iam_policy.jwt_private_key_access.arn
}

# Outputs for JWT configuration
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

output "jwt_public_key_access_policy_arn" {
  description = "ARN of the IAM policy for JWT public key access"
  value       = aws_iam_policy.jwt_public_key_access.arn
}

output "jwt_private_key_access_policy_arn" {
  description = "ARN of the IAM policy for JWT private key access"
  value       = aws_iam_policy.jwt_private_key_access.arn
}