# Example usage of the Kong API Gateway Security Module

# Production environment configuration
module "api_gateway_security_production" {
  source = "../"
  
  environment = "production"
  allowed_origins = [
    "https://app.dollarfunding.com",
    "https://admin.dollarfunding.com"
  ]
  admin_api_allowed_ips = [
    "10.0.0.0/8",     # Internal network
    "192.168.1.0/24", # VPN network
  ]
  
  # Production rate limits
  authenticated_rate_limit = 60
  unauthenticated_rate_limit = 10
  admin_rate_limit = 120
  operations_rate_limit = 90
  
  # JWT configuration
  jwt_issuer = "dollarfunding-mca"
  jwt_audience = ["mca-application"]
  jwt_token_expiration = 3600        # 1 hour
  jwt_refresh_token_expiration = 604800  # 7 days
  jwt_key_rotation_enabled = true
  jwt_key_rotation_interval_days = 90
  
  # Enable all security features
  enable_request_transformation = true
  enable_response_transformation = true
  enable_audit_logging = true
}

# Staging environment configuration
module "api_gateway_security_staging" {
  source = "../"
  
  environment = "staging"
  allowed_origins = [
    "https://staging.app.dollarfunding.com",
    "https://staging.admin.dollarfunding.com",
    "http://localhost:3000"  # Allow local development
  ]
  admin_api_allowed_ips = [
    "10.0.0.0/8",     # Internal network
    "192.168.1.0/24", # VPN network
    "203.0.113.0/24"  # Development office
  ]
  
  # Higher rate limits for testing
  authenticated_rate_limit = 120
  unauthenticated_rate_limit = 30
  admin_rate_limit = 240
  operations_rate_limit = 180
  
  # JWT configuration
  jwt_issuer = "dollarfunding-mca-staging"
  jwt_audience = ["mca-application-staging"]
  jwt_token_expiration = 7200        # 2 hours for testing
  jwt_refresh_token_expiration = 1209600  # 14 days for testing
  jwt_key_rotation_enabled = true
  jwt_key_rotation_interval_days = 30  # More frequent rotation in staging
  
  # Enable all security features
  enable_request_transformation = true
  enable_response_transformation = true
  enable_audit_logging = true
}

# Development environment configuration
module "api_gateway_security_development" {
  source = "../"
  
  environment = "development"
  allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://dev.app.dollarfunding.com"
  ]
  admin_api_allowed_ips = [
    "0.0.0.0/0"  # Allow all IPs in development (not recommended for other environments)
  ]
  
  # Very high rate limits for development
  authenticated_rate_limit = 600
  unauthenticated_rate_limit = 300
  admin_rate_limit = 1200
  operations_rate_limit = 900
  
  # JWT configuration
  jwt_issuer = "dollarfunding-mca-dev"
  jwt_audience = ["mca-application-dev"]
  jwt_token_expiration = 86400       # 24 hours for development
  jwt_refresh_token_expiration = 2592000  # 30 days for development
  jwt_key_rotation_enabled = false   # Disable key rotation in development
  
  # Disable some security features in development for easier debugging
  enable_request_transformation = false
  enable_response_transformation = false
  enable_audit_logging = true
}