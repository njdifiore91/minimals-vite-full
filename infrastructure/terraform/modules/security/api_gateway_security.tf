# API Gateway Security Configuration for Kong
# This module implements security configurations for the Kong API Gateway including:
# - Rate limiting with different limits for authenticated and unauthenticated requests
# - Strict CORS policies with explicit allowed origins, methods, and headers
# - JWT validation using RS256 algorithm with public key verification and rotation
# - IP restrictions for admin endpoints with audit logging
# - Request transformation for security headers and sanitization

# Variables for the module
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["https://app.dollarfunding.com"]
}

variable "admin_api_allowed_ips" {
  description = "List of IP addresses allowed to access admin endpoints"
  type        = list(string)
  default     = []
}

variable "jwt_issuer" {
  description = "JWT issuer to validate"
  type        = string
  default     = "dollarfunding-mca"
}

variable "jwt_audience" {
  description = "JWT audience to validate"
  type        = list(string)
  default     = ["mca-application"]
}

variable "jwt_token_expiration" {
  description = "JWT token expiration time in seconds"
  type        = number
  default     = 3600 # 1 hour
}

variable "jwt_refresh_token_expiration" {
  description = "JWT refresh token expiration time in seconds"
  type        = number
  default     = 604800 # 7 days
}

variable "authenticated_rate_limit" {
  description = "Rate limit for authenticated requests (per minute)"
  type        = number
  default     = 60
}

variable "unauthenticated_rate_limit" {
  description = "Rate limit for unauthenticated requests (per minute)"
  type        = number
  default     = 10
}

variable "admin_rate_limit" {
  description = "Rate limit for admin role requests (per minute)"
  type        = number
  default     = 120
}

variable "operations_rate_limit" {
  description = "Rate limit for operations staff role requests (per minute)"
  type        = number
  default     = 90
}

variable "enable_request_transformation" {
  description = "Enable request transformation for security headers"
  type        = bool
  default     = true
}

variable "enable_response_transformation" {
  description = "Enable response transformation for security headers"
  type        = bool
  default     = true
}

variable "enable_audit_logging" {
  description = "Enable audit logging for security events"
  type        = bool
  default     = true
}

variable "jwt_key_rotation_enabled" {
  description = "Enable JWT key rotation"
  type        = bool
  default     = true
}

variable "jwt_key_rotation_interval_days" {
  description = "Interval in days for JWT key rotation"
  type        = number
  default     = 90
}

# Local variables
locals {
  cors_config = {
    origins         = var.allowed_origins
    methods         = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    headers         = ["Accept", "Accept-Version", "Content-Length", "Content-MD5", "Content-Type", "Date", "X-Auth-Token", "Authorization"]
    exposed_headers = ["X-Auth-Token", "X-Request-ID"]
    credentials     = true
    max_age         = 3600
    preflight_continue = false
  }
  
  rate_limit_tiers = {
    admin = {
      second = null
      minute = var.admin_rate_limit
      hour   = var.admin_rate_limit * 10
      day    = var.admin_rate_limit * 60
    }
    operations = {
      second = null
      minute = var.operations_rate_limit
      hour   = var.operations_rate_limit * 10
      day    = var.operations_rate_limit * 60
    }
    authenticated = {
      second = null
      minute = var.authenticated_rate_limit
      hour   = var.authenticated_rate_limit * 10
      day    = var.authenticated_rate_limit * 60
    }
    unauthenticated = {
      second = null
      minute = var.unauthenticated_rate_limit
      hour   = var.unauthenticated_rate_limit * 10
      day    = var.unauthenticated_rate_limit * 60
    }
  }
  
  jwt_config = {
    issuer                 = var.jwt_issuer
    audience               = var.jwt_audience
    token_expiration       = var.jwt_token_expiration
    refresh_token_expiration = var.jwt_refresh_token_expiration
    algorithm              = "RS256"
    claims_to_verify       = ["exp", "nbf"]
    key_rotation_enabled   = var.jwt_key_rotation_enabled
    key_rotation_interval  = var.jwt_key_rotation_interval_days
  }
  
  security_headers = {
    request = {
      add = {
        "X-Frame-Options" = "DENY"
        "X-Content-Type-Options" = "nosniff"
        "X-XSS-Protection" = "1; mode=block"
        "Content-Security-Policy" = "default-src 'self'"
        "Strict-Transport-Security" = "max-age=31536000; includeSubDomains"
      }
      remove = ["Server"]
    }
    response = {
      add = {
        "X-Frame-Options" = "DENY"
        "X-Content-Type-Options" = "nosniff"
        "X-XSS-Protection" = "1; mode=block"
        "Content-Security-Policy" = "default-src 'self'"
        "Strict-Transport-Security" = "max-age=31536000; includeSubDomains"
      }
      remove = ["Server", "X-Powered-By"]
    }
  }
}

# Resource for JWT public/private key storage in AWS SSM Parameter Store
resource "aws_ssm_parameter" "jwt_public_key" {
  name        = "/kong/${var.environment}/jwt/public_key"
  description = "Public key for JWT validation in Kong API Gateway"
  type        = "SecureString"
  value       = file("${path.module}/files/jwt_public_key.pem")
  
  tags = {
    Environment = var.environment
    Service     = "kong-api-gateway"
    Purpose     = "jwt-validation"
  }
}

resource "aws_ssm_parameter" "jwt_private_key" {
  name        = "/kong/${var.environment}/jwt/private_key"
  description = "Private key for JWT signing in Kong API Gateway"
  type        = "SecureString"
  value       = file("${path.module}/files/jwt_private_key.pem")
  
  tags = {
    Environment = var.environment
    Service     = "kong-api-gateway"
    Purpose     = "jwt-signing"
  }
}

# Resource for JWT key rotation if enabled
resource "null_resource" "jwt_key_rotation" {
  count = var.jwt_key_rotation_enabled ? 1 : 0
  
  triggers = {
    rotation_time = formatdate("YYYY-MM-DD", timeadd(timestamp(), "${var.jwt_key_rotation_interval_days * 24}h"))
  }
  
  provisioner "local-exec" {
    command = <<-EOT
      # Generate new RSA key pair for JWT
      openssl genrsa -out ${path.module}/files/jwt_private_key_new.pem 2048
      openssl rsa -in ${path.module}/files/jwt_private_key_new.pem -pubout -out ${path.module}/files/jwt_public_key_new.pem
      
      # Update AWS SSM parameters with new keys
      aws ssm put-parameter --name "/kong/${var.environment}/jwt/public_key_new" --type "SecureString" --value file://${path.module}/files/jwt_public_key_new.pem --overwrite
      aws ssm put-parameter --name "/kong/${var.environment}/jwt/private_key_new" --type "SecureString" --value file://${path.module}/files/jwt_private_key_new.pem --overwrite
    EOT
  }
}

# Create directory structure for template files
resource "null_resource" "create_template_directories" {
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/templates ${path.module}/output/${var.environment} ${path.module}/files"
  }
}

# Generate Kong API Gateway configuration files

# Rate limiting configuration for different user roles
resource "local_file" "rate_limiting_admin_config" {
  content = templatefile("${path.module}/templates/rate_limiting_role.tpl", {
    rate_limit = local.rate_limit_tiers.admin
    role       = "admin"
    limit_by   = "credential"
  })
  filename = "${path.module}/output/${var.environment}/kong_rate_limiting_admin.json"
  depends_on = [null_resource.create_template_directories]
}

resource "local_file" "rate_limiting_operations_config" {
  content = templatefile("${path.module}/templates/rate_limiting_role.tpl", {
    rate_limit = local.rate_limit_tiers.operations
    role       = "operations"
    limit_by   = "credential"
  })
  filename = "${path.module}/output/${var.environment}/kong_rate_limiting_operations.json"
  depends_on = [null_resource.create_template_directories]
}

resource "local_file" "rate_limiting_authenticated_config" {
  content = templatefile("${path.module}/templates/rate_limiting_role.tpl", {
    rate_limit = local.rate_limit_tiers.authenticated
    role       = "authenticated"
    limit_by   = "credential"
  })
  filename = "${path.module}/output/${var.environment}/kong_rate_limiting_authenticated.json"
  depends_on = [null_resource.create_template_directories]
}

resource "local_file" "rate_limiting_unauthenticated_config" {
  content = templatefile("${path.module}/templates/rate_limiting_role.tpl", {
    rate_limit = local.rate_limit_tiers.unauthenticated
    role       = "unauthenticated"
    limit_by   = "ip"
  })
  filename = "${path.module}/output/${var.environment}/kong_rate_limiting_unauthenticated.json"
  depends_on = [null_resource.create_template_directories]
}

# CORS configuration
resource "local_file" "cors_config" {
  content = templatefile("${path.module}/templates/cors.tpl", {
    cors_config = local.cors_config
  })
  filename = "${path.module}/output/${var.environment}/kong_cors.json"
  depends_on = [null_resource.create_template_directories]
}

# JWT configuration
resource "local_file" "jwt_config" {
  content = templatefile("${path.module}/templates/jwt.tpl", {
    jwt_config = local.jwt_config
    public_key_param = aws_ssm_parameter.jwt_public_key.name
  })
  filename = "${path.module}/output/${var.environment}/kong_jwt.json"
  depends_on = [null_resource.create_template_directories]
}

# IP restriction configuration for admin endpoints
resource "local_file" "ip_restriction_config" {
  content = templatefile("${path.module}/templates/ip_restriction.tpl", {
    allowed_ips = var.admin_api_allowed_ips
    enable_logging = var.enable_audit_logging
  })
  filename = "${path.module}/output/${var.environment}/kong_ip_restriction.json"
  depends_on = [null_resource.create_template_directories]
}

# Request transformation configuration for security headers
resource "local_file" "request_transformer_config" {
  count = var.enable_request_transformation ? 1 : 0
  content = templatefile("${path.module}/templates/request_transformer.tpl", {
    headers = local.security_headers.request
  })
  filename = "${path.module}/output/${var.environment}/kong_request_transformer.json"
  depends_on = [null_resource.create_template_directories]
}

# Response transformation configuration for security headers
resource "local_file" "response_transformer_config" {
  count = var.enable_response_transformation ? 1 : 0
  content = templatefile("${path.module}/templates/response_transformer.tpl", {
    headers = local.security_headers.response
  })
  filename = "${path.module}/output/${var.environment}/kong_response_transformer.json"
  depends_on = [null_resource.create_template_directories]
}

# Audit logging configuration
resource "local_file" "audit_logging_config" {
  count = var.enable_audit_logging ? 1 : 0
  content = templatefile("${path.module}/templates/audit_logging.tpl", {
    environment = var.environment
  })
  filename = "${path.module}/output/${var.environment}/kong_audit_logging.json"
  depends_on = [null_resource.create_template_directories]
}

# Template files for Kong API Gateway plugins

# Template file for role-based rate limiting configuration
resource "local_file" "rate_limiting_role_template" {
  depends_on = [null_resource.create_template_directories]
  content    = <<-EOT
{
  "name": "rate-limiting",
  "config": {
    "second": $${rate_limit.second != null ? rate_limit.second : "null"},
    "minute": $${rate_limit.minute},
    "hour": $${rate_limit.hour},
    "day": $${rate_limit.day},
    "policy": "local",
    "limit_by": "$${limit_by}",
    "fault_tolerant": true,
    "hide_client_headers": false
  },
  "tags": ["role:$${role}"]
}
EOT
  filename   = "${path.module}/templates/rate_limiting_role.tpl"
}

# Template file for CORS configuration
resource "local_file" "cors_template" {
  depends_on = [null_resource.create_template_directories]
  content    = <<-EOT
{
  "name": "cors",
  "config": {
    "origins": [
      ${join(",
      ", formatlist("\"%s\"", cors_config.origins))}
    ],
    "methods": [
      ${join(",
      ", formatlist("\"%s\"", cors_config.methods))}
    ],
    "headers": [
      ${join(",
      ", formatlist("\"%s\"", cors_config.headers))}
    ],
    "exposed_headers": [
      ${join(",
      ", formatlist("\"%s\"", cors_config.exposed_headers))}
    ],
    "credentials": ${cors_config.credentials},
    "max_age": ${cors_config.max_age},
    "preflight_continue": ${cors_config.preflight_continue}
  }
}
EOT
  filename   = "${path.module}/templates/cors.tpl"
}

# Template file for JWT configuration
resource "local_file" "jwt_template" {
  depends_on = [null_resource.create_template_directories]
  content    = <<-EOT
{
  "name": "jwt",
  "config": {
    "key_claim_name": "iss",
    "claims_to_verify": [
      ${join(",
      ", formatlist("\"%s\"", jwt_config.claims_to_verify))}
    ],
    "secret_is_base64": false,
    "run_on_preflight": true,
    "maximum_expiration": ${jwt_config.token_expiration},
    "algorithm": "${jwt_config.algorithm}",
    "header_names": ["Authorization"],
    "uri_param_names": ["jwt"],
    "cookie_names": [],
    "issuers": ["${jwt_config.issuer}"],
    "audience": [
      ${join(",
      ", formatlist("\"%s\"", jwt_config.audience))}
    ]
  }
}
EOT
  filename   = "${path.module}/templates/jwt.tpl"
}

# Template file for IP restriction configuration
resource "local_file" "ip_restriction_template" {
  depends_on = [null_resource.create_template_directories]
  content    = <<-EOT
{
  "name": "ip-restriction",
  "config": {
    "allow": [
      ${join(",
      ", formatlist("\"%s\"", allowed_ips))}
    ],
    "deny": [],
    "status": 403,
    "message": "Access denied: your IP address is not allowed to access this resource"
  },
  "tags": ["security", "admin-protection", "audit:$${enable_logging ? "enabled" : "disabled"}"]  
}
EOT
  filename   = "${path.module}/templates/ip_restriction.tpl"
}

# Template file for request transformer configuration
resource "local_file" "request_transformer_template" {
  depends_on = [null_resource.create_template_directories]
  content    = <<-EOT
{
  "name": "request-transformer",
  "config": {
    "add": {
      "headers": [
        ${join(",
        ", [for k, v in headers.add : "\"${k}:${v}\"" ])}
      ]
    },
    "remove": {
      "headers": [
        ${join(",
        ", formatlist("\"%s\"", headers.remove))}
      ]
    }
  },
  "tags": ["security", "request-transformation"]
}
EOT
  filename   = "${path.module}/templates/request_transformer.tpl"
}

# Template file for response transformer configuration
resource "local_file" "response_transformer_template" {
  depends_on = [null_resource.create_template_directories]
  content    = <<-EOT
{
  "name": "response-transformer",
  "config": {
    "add": {
      "headers": [
        ${join(",
        ", [for k, v in headers.add : "\"${k}:${v}\"" ])}
      ]
    },
    "remove": {
      "headers": [
        ${join(",
        ", formatlist("\"%s\"", headers.remove))}
      ]
    }
  },
  "tags": ["security", "response-transformation"]
}
EOT
  filename   = "${path.module}/templates/response_transformer.tpl"
}

# Template file for audit logging configuration
resource "local_file" "audit_logging_template" {
  depends_on = [null_resource.create_template_directories]
  content    = <<-EOT
{
  "name": "file-log",
  "config": {
    "path": "/var/log/kong/audit_${environment}.log",
    "reopen": true,
    "custom_fields_by_lua": {
      "user_id": "return kong.client.get_consumer() and kong.client.get_consumer().id or \"anonymous\"",
      "service_id": "return kong.router.get_service() and kong.router.get_service().id or \"unknown\"",
      "route_id": "return kong.router.get_route() and kong.router.get_route().id or \"unknown\"",
      "request_timestamp": "return os.time()",
      "environment": "\"${environment}\""
    }
  },
  "tags": ["audit", "security"]
}
EOT
  filename   = "${path.module}/templates/audit_logging.tpl"
}

# Output the paths to the generated configuration files
output "rate_limiting_configs" {
  description = "Paths to the generated rate limiting configuration files"
  value = {
    admin         = local_file.rate_limiting_admin_config.filename
    operations    = local_file.rate_limiting_operations_config.filename
    authenticated = local_file.rate_limiting_authenticated_config.filename
    unauthenticated = local_file.rate_limiting_unauthenticated_config.filename
  }
}

output "cors_config_path" {
  description = "Path to the generated CORS configuration file"
  value       = local_file.cors_config.filename
}

output "jwt_config_path" {
  description = "Path to the generated JWT configuration file"
  value       = local_file.jwt_config.filename
}

output "ip_restriction_config_path" {
  description = "Path to the generated IP restriction configuration file"
  value       = local_file.ip_restriction_config.filename
}

output "request_transformer_config_path" {
  description = "Path to the generated request transformer configuration file"
  value       = var.enable_request_transformation ? local_file.request_transformer_config[0].filename : null
}

output "response_transformer_config_path" {
  description = "Path to the generated response transformer configuration file"
  value       = var.enable_response_transformation ? local_file.response_transformer_config[0].filename : null
}

output "audit_logging_config_path" {
  description = "Path to the generated audit logging configuration file"
  value       = var.enable_audit_logging ? local_file.audit_logging_config[0].filename : null
}

# Output the SSM parameter names for the JWT keys
output "jwt_public_key_param" {
  description = "SSM parameter name for the JWT public key"
  value       = aws_ssm_parameter.jwt_public_key.name
}

output "jwt_private_key_param" {
  description = "SSM parameter name for the JWT private key"
  value       = aws_ssm_parameter.jwt_private_key.name
}