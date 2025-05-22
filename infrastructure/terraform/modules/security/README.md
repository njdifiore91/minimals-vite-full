# Kong API Gateway Security Module

This Terraform module implements comprehensive security configurations for the Kong API Gateway in the MCA Application Processing System. It provides a robust security boundary for all external requests to backend microservices.

## Features

- **Rate Limiting**: Tiered rate limiting based on authentication status and user roles
  - Admin: 120 requests per minute
  - Operations Staff: 90 requests per minute
  - Authenticated Users: 60 requests per minute
  - Unauthenticated Requests: 10 requests per minute

- **CORS Policies**: Strict Cross-Origin Resource Sharing with explicit allowed origins, methods, and headers

- **JWT Validation**: Centralized JWT validation using RS256 algorithm with public key verification
  - Token expiration verification
  - Issuer and audience validation
  - Support for key rotation

- **IP Restrictions**: IP-based access controls for administrative endpoints with audit logging

- **Request/Response Transformation**: Security headers and request sanitization

- **Audit Logging**: Comprehensive logging of security events

## Usage

```hcl
module "api_gateway_security" {
  source = "../modules/security"
  
  environment = "production"
  allowed_origins = ["https://app.dollarfunding.com"]
  admin_api_allowed_ips = ["10.0.0.0/8", "192.168.1.0/24"]
  
  # Optional: Override default rate limits
  authenticated_rate_limit = 60
  unauthenticated_rate_limit = 10
  admin_rate_limit = 120
  operations_rate_limit = 90
  
  # Optional: JWT configuration
  jwt_issuer = "dollarfunding-mca"
  jwt_audience = ["mca-application"]
  jwt_token_expiration = 3600
  jwt_refresh_token_expiration = 604800
  jwt_key_rotation_enabled = true
  jwt_key_rotation_interval_days = 90
  
  # Optional: Enable/disable features
  enable_request_transformation = true
  enable_response_transformation = true
  enable_audit_logging = true
}
```

## Requirements

- Terraform >= 0.14
- AWS Provider >= 3.0
- Kong API Gateway >= 3.5.0

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| environment | Environment name (e.g., development, staging, production) | `string` | n/a | yes |
| allowed_origins | List of allowed origins for CORS | `list(string)` | `["https://app.dollarfunding.com"]` | no |
| admin_api_allowed_ips | List of IP addresses allowed to access admin endpoints | `list(string)` | `[]` | no |
| jwt_issuer | JWT issuer to validate | `string` | `"dollarfunding-mca"` | no |
| jwt_audience | JWT audience to validate | `list(string)` | `["mca-application"]` | no |
| jwt_token_expiration | JWT token expiration time in seconds | `number` | `3600` | no |
| jwt_refresh_token_expiration | JWT refresh token expiration time in seconds | `number` | `604800` | no |
| authenticated_rate_limit | Rate limit for authenticated requests (per minute) | `number` | `60` | no |
| unauthenticated_rate_limit | Rate limit for unauthenticated requests (per minute) | `number` | `10` | no |
| admin_rate_limit | Rate limit for admin role requests (per minute) | `number` | `120` | no |
| operations_rate_limit | Rate limit for operations staff role requests (per minute) | `number` | `90` | no |
| enable_request_transformation | Enable request transformation for security headers | `bool` | `true` | no |
| enable_response_transformation | Enable response transformation for security headers | `bool` | `true` | no |
| enable_audit_logging | Enable audit logging for security events | `bool` | `true` | no |
| jwt_key_rotation_enabled | Enable JWT key rotation | `bool` | `true` | no |
| jwt_key_rotation_interval_days | Interval in days for JWT key rotation | `number` | `90` | no |

## Outputs

| Name | Description |
|------|-------------|
| rate_limiting_configs | Paths to the generated rate limiting configuration files |
| cors_config_path | Path to the generated CORS configuration file |
| jwt_config_path | Path to the generated JWT configuration file |
| ip_restriction_config_path | Path to the generated IP restriction configuration file |
| request_transformer_config_path | Path to the generated request transformer configuration file |
| response_transformer_config_path | Path to the generated response transformer configuration file |
| audit_logging_config_path | Path to the generated audit logging configuration file |
| jwt_public_key_param | SSM parameter name for the JWT public key |
| jwt_private_key_param | SSM parameter name for the JWT private key |

## Implementation Notes

1. **JWT Key Rotation**: The module supports automatic JWT key rotation by generating new key pairs and storing them in AWS SSM Parameter Store. The rotation interval is configurable.

2. **Rate Limiting Tiers**: Different rate limiting configurations are generated for various user roles to implement tiered access control.

3. **Security Headers**: The module adds important security headers to requests and responses, including Content-Security-Policy, X-XSS-Protection, and Strict-Transport-Security.

4. **Audit Logging**: When enabled, all security events are logged to a dedicated audit log file with detailed information about the request, user, and accessed service.

5. **IP Restrictions**: Administrative endpoints are protected with IP-based access controls, allowing access only from specified IP addresses or CIDR ranges.